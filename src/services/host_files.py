from __future__ import annotations

import tempfile
from pathlib import Path
import inspect

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

            output = exec_instance.start(detach=False)
            stdout_data, stderr_data = await self._collect_stream_output(output)

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
            await self._ensure_helper_image()
            volumes = {}
            for allowed_path in self._settings.allowed_mount_paths:
                volumes[allowed_path] = {"bind": allowed_path, "mode": "rw"}

            config = {
                "Image": self._settings.helper_image,
                "Cmd": ["/bin/sh", "-c", command],
                "HostConfig": {
                    "Binds": [f"{k}:{v['bind']}:{v['mode']}" for k, v in volumes.items()],
                    "NetworkMode": "host",
                    "CapAdd": ["NET_ADMIN"],
                    "AutoRemove": True
                }
            }

            container = await self._client.containers.create(config=config)
            await container.start()

            await container.wait()
            logs = container.log(stdout=True, stderr=True)
            if inspect.isawaitable(logs):
                logs = await logs
            output = await self._collect_logs_output(logs)
            return 0, output, ""

        except aiodocker.exceptions.DockerError as exc:
            raise HostServiceError(str(exc)) from exc

    async def _ensure_helper_image(self) -> None:
        try:
            await self._client.images.inspect(self._settings.helper_image)
            return
        except aiodocker.exceptions.DockerError as exc:
            if exc.status != 404:
                raise HostServiceError(str(exc)) from exc

        try:
            pull_result = self._client.images.pull(self._settings.helper_image)
            if inspect.isawaitable(pull_result):
                pull_result = await pull_result

            if hasattr(pull_result, "__aiter__"):
                async for _ in pull_result:
                    pass
            elif isinstance(pull_result, (list, tuple)):
                return
        except aiodocker.exceptions.DockerError as exc:
            raise HostServiceError(str(exc)) from exc

    async def _collect_stream_output(self, stream: object) -> tuple[bytes, bytes]:
        stdout_data = b""
        stderr_data = b""

        if hasattr(stream, "__aiter__"):
            async for msg in stream:
                stream_id = getattr(msg, "stream", None)
                chunk = self._message_to_bytes(msg)
                if stream_id == 2:
                    stderr_data += chunk
                else:
                    stdout_data += chunk
            return stdout_data, stderr_data

        read_out = getattr(stream, "read_out", None)
        read_err = getattr(stream, "read_err", None)
        if callable(read_out) or callable(read_err):
            while True:
                out_chunk_raw = await read_out() if callable(read_out) else None
                err_chunk_raw = await read_err() if callable(read_err) else None
                out_chunk = self._message_to_bytes(out_chunk_raw) if out_chunk_raw else b""
                err_chunk = self._message_to_bytes(err_chunk_raw) if err_chunk_raw else b""
                if not out_chunk and not err_chunk:
                    break
                stdout_data += out_chunk
                stderr_data += err_chunk
            return stdout_data, stderr_data

        read_any = getattr(stream, "read", None)
        if callable(read_any):
            while True:
                chunk_raw = await read_any()
                if not chunk_raw:
                    break
                stdout_data += self._message_to_bytes(chunk_raw)
            return stdout_data, stderr_data

        raise HostServiceError("Unsupported stream type returned from Docker exec")

    async def _collect_logs_output(self, logs: object) -> str:
        if isinstance(logs, (list, tuple)):
            return "".join(
                self._message_to_bytes(msg).decode("utf-8", errors="replace")
                for msg in logs
            )

        if hasattr(logs, "__aiter__"):
            output = ""
            async for msg in logs:
                output += self._message_to_bytes(msg).decode("utf-8", errors="replace")
            return output

        read_any = getattr(logs, "read", None)
        if callable(read_any):
            output = ""
            while True:
                chunk = await read_any()
                if not chunk:
                    break
                output += self._message_to_bytes(chunk).decode("utf-8", errors="replace")
            return output

        return str(logs)

    def _message_to_bytes(self, msg: object) -> bytes:
        if msg is None:
            return b""
        if isinstance(msg, (bytes, bytearray)):
            return bytes(msg)
        if isinstance(msg, str):
            return msg.encode("utf-8", errors="replace")

        if hasattr(msg, "data"):
            data = msg.data
            if isinstance(data, (bytes, bytearray)):
                return bytes(data)
            if isinstance(data, str):
                return data.encode("utf-8", errors="replace")
            if data is not None:
                return self._message_to_bytes(data)

        if isinstance(msg, dict):
            for key in ("data", "stream", "message", "content"):
                if key in msg:
                    data = msg[key]
                    if isinstance(data, (bytes, bytearray)):
                        return bytes(data)
                    if isinstance(data, str):
                        return data.encode("utf-8", errors="replace")
                    if data is not None:
                        return self._message_to_bytes(data)

        return str(msg).encode("utf-8", errors="replace")

