import aiodocker

from src.services.management.exceptions import (
    DockerServiceError,
    ContainerNotFoundError,
    ImageNotFoundError,
)


class DockerService:
    def __init__(self, docker_client: aiodocker.Docker):
        self._client = docker_client

    async def is_docker_available(self) -> bool:
        try:
            await self._client.version()
            return True
        except Exception:
            return False

    async def container_exists(self, name: str) -> bool:
        try:
            await self._client.containers.get(name)
            return True
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                return False
            raise DockerServiceError(str(exc)) from exc

    async def get_container_status(self, name: str) -> str | None:
        try:
            container = await self._client.containers.get(name)
            info = await container.show()
            return info.get("State", {}).get("Status")
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                return None
            raise DockerServiceError(str(exc)) from exc

    async def create_container(self, image: str, name: str, **kwargs) -> str:
        try:
            if "Cmd" not in kwargs and "cmd" not in kwargs:
                kwargs["Cmd"] = ["tail", "-f", "/dev/null"]
            config = {
                "Image": image,
                "HostConfig": self._build_host_config(kwargs),
                **{k: v for k, v in kwargs.items() if k not in ["detach", "network_mode", "cap_add", "volumes", "restart_policy"]}
            }

            container = await self._client.containers.create(config=config, name=name)
            return container.id
        except aiodocker.exceptions.DockerError as exc:
            raise DockerServiceError(str(exc)) from exc

    async def start_container(self, name: str) -> None:
        try:
            container = await self._client.containers.get(name)
            await container.start()
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                raise ContainerNotFoundError(name) from exc
            raise DockerServiceError(str(exc)) from exc

    async def stop_container(self, name: str, timeout: int = 10) -> None:
        try:
            container = await self._client.containers.get(name)
            await container.stop(timeout=timeout)
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                raise ContainerNotFoundError(name) from exc
            raise DockerServiceError(str(exc)) from exc

    async def remove_container(self, name: str, force: bool = False) -> None:
        try:
            container = await self._client.containers.get(name)
            await container.delete(force=force)
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                raise ContainerNotFoundError(name) from exc
            raise DockerServiceError(str(exc)) from exc

    async def get_container_logs(self, name: str, tail: int = 100) -> str:
        try:
            container = await self._client.containers.get(name)
            logs = await container.log(stdout=True, stderr=True, tail=tail)
            if isinstance(logs, (list, tuple)):
                return "".join(
                    msg.decode("utf-8", errors="replace") if isinstance(msg, (bytes, bytearray)) else str(msg)
                    for msg in logs
                )
            return str(logs)
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                raise ContainerNotFoundError(name) from exc
            raise DockerServiceError(str(exc)) from exc

    async def image_exists(self, image: str) -> bool:
        try:
            await self._client.images.inspect(image)
            return True
        except aiodocker.exceptions.DockerError as exc:
            if exc.status == 404:
                return False
            raise DockerServiceError(str(exc)) from exc

    async def pull_image(self, image: str) -> None:
        try:
            async for _ in self._client.images.pull(image):
                pass
        except aiodocker.exceptions.DockerError as exc:
            raise ImageNotFoundError(str(exc)) from exc

    async def wait_for_container_ready(self, name: str, timeout: int = 30) -> bool:
        """Wait for container to be in running state"""
        import asyncio

        try:
            start_time = asyncio.get_event_loop().time()

            while True:
                status = await self.get_container_status(name)

                if status == "running":
                    return True

                if status is None:
                    raise ContainerNotFoundError(name)

                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    raise DockerServiceError(
                        f"Timeout waiting for container {name} to be ready. Current status: {status}"
                    )

                await asyncio.sleep(1)

        except ContainerNotFoundError:
            raise
        except aiodocker.exceptions.DockerError as exc:
            raise DockerServiceError(str(exc)) from exc

    def _build_host_config(self, kwargs: dict) -> dict:
        """Build HostConfig from kwargs for aiodocker compatibility"""
        host_config = {}

        if "network_mode" in kwargs:
            host_config["NetworkMode"] = kwargs["network_mode"]

        if "cap_add" in kwargs:
            host_config["CapAdd"] = kwargs["cap_add"]

        if "volumes" in kwargs:
            binds = []
            for src, bind_info in kwargs["volumes"].items():
                bind_str = f"{src}:{bind_info['bind']}:{bind_info.get('mode', 'rw')}"
                binds.append(bind_str)
            host_config["Binds"] = binds

        if "restart_policy" in kwargs:
            host_config["RestartPolicy"] = kwargs["restart_policy"]

        if "devices" in kwargs:
            host_config["Devices"] = kwargs["devices"]

        return host_config


