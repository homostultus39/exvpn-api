import aiodocker

from src.utils.settings import get_settings

_docker_client: aiodocker.Docker | None = None


async def get_docker_client() -> aiodocker.Docker:
    """Get or create async Docker client with connection pooling"""
    global _docker_client

    if _docker_client is None:
        settings = get_settings()
        _docker_client = aiodocker.Docker(url=f"unix://{settings.docker_socket_path}")

    return _docker_client


async def close_docker_client() -> None:
    """Close Docker client connection pool"""
    global _docker_client

    if _docker_client is not None:
        await _docker_client.close()
        _docker_client = None