from typing import Annotated

from fastapi import Depends

from src.services.awg_configurator import AWGService
from src.services.client_configurator import ConfigService
from src.services.container_manager import DockerService
from src.services.docker_client import get_docker_client
from src.services.host_files import HostService
from src.services.key_generator import KeyService


async def get_docker_service() -> DockerService:
    """Get Docker service with connection pool"""
    docker_client = await get_docker_client()
    return DockerService(docker_client)


async def get_host_service() -> HostService:
    """Get Host service for file operations and container exec"""
    docker_client = await get_docker_client()
    return HostService(docker_client)


def get_key_service() -> KeyService:
    """Get Key service for generating keys"""
    return KeyService()


async def get_awg_service(
    host_service: Annotated[HostService, Depends(get_host_service)],
    docker_service: Annotated[DockerService, Depends(get_docker_service)],
    key_service: Annotated[KeyService, Depends(get_key_service)]
) -> AWGService:
    """Get AWG service with all dependencies"""
    return AWGService(
        host_service=host_service,
        docker_service=docker_service,
        key_service=key_service
    )


def get_config_service() -> ConfigService:
    """Get Config service for generating client configs"""
    return ConfigService()
