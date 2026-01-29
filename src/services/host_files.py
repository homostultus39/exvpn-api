from __future__ import annotations

import tempfile
from pathlib import Path

import aiofiles
import aiodocker

from src.services.management.exceptions import (
    ContainerNotFoundError,
    FileAccessError,
    HostServiceError,
)
from src.utils.settings import get_settings


class HostService:
    def __init__(self, docker_client: aiodocker.Docker):
        self._client = docker_client
        self._settings = get_settings()

    async def read_file(self, path: str) -> str:
        try:
            async with aiofiles.open(path, mode="r", encoding="utf-8") as f:
                return await f.read()
        except (FileNotFoundError, PermissionError, OSError) as exc:
            raise FileAccessError(str(exc)) from exc

    async def write_file(self, path: str, content: str) -> None:
        target = Path(path)
        try:
            target.parent.mkdir(parents=True, exist_ok=True)

            temp_path = None
            async with aiofiles.tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=str(target.parent)
            ) as tmp_file:
                await tmp_file.write(content)
                temp_path = Path(tmp_file.name)

            if temp_path:
                temp_path.replace(target)
        except (PermissionError, OSError) as exc:
            raise FileAccessError(str(exc)) from exc

    def file_exists(self, path: str) -> bool:
        return Path(path).exists()

    async def exec_in_container(
        self,
        container_name: str,
        command: str,
        user: str | None = None
    ) -> tuple[int, str, str]:
        try:
            container = await self._client.containers.get(container_name)
            exec_instance = await container.exec(
                cmd=["/bin/sh", "-c", command],
                user=user,
                stdout=True,
                stderr=True
            )

            output = await exec_instance.start(detach=False)

            stdout_data = b""
            stderr_data = b""
            async for msg in output:
                if msg.stream == 1:  # stdout
                    stdout_data += msg.data
                elif msg.stream == 2:  # stderr
                    stderr_data += msg.data

            inspect = await exec_instance.inspect()
            exit_code = inspect.get("ExitCode", 0)

            return exit_code, stdout_data.decode("utf-8"), stderr_data.decode("utf-8")

        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                raise ContainerNotFoundError(container_name) from exc
            raise HostServiceError(str(exc)) from exc

    async def execute_on_host(self, command: str) -> tuple[int, str, str]:
        """
        Execute command on host using helper container with restricted volume mounts
        Security: Only mounts paths from allowed_mount_paths setting
        """
        try:
            volumes = {}
            for allowed_path in self._settings.allowed_mount_paths:
                volumes[allowed_path] = {"bind": allowed_path, "mode": "rw"}

            config = {
                "Image": self._settings.helper_image,
                "Cmd": ["/bin/sh", "-c", command],
                "HostConfig": {
                    "Binds": [f"{k}:{v['bind']}:{v['mode']}" for k, v in volumes.items()],
                    "NetworkMode": "host",
                    "AutoRemove": True
                }
            }

            container = await self._client.containers.create(config=config)
            await container.start()

            await container.wait()
            logs = await container.log(stdout=True, stderr=True)

            output = "".join([msg for msg in logs])
            return 0, output, ""

        except aiodocker.exceptions.DockerError as exc:
            raise HostServiceError(str(exc)) from exc

