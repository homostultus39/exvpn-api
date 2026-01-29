from src.services.awg_configurator import AWGService
from src.services.client_configurator import ConfigService
from src.services.docker_client import get_docker_client
from src.services.container_manager import DockerService
from src.services.host_files import HostService
from src.services.key_generator import KeyService


def get_key_service() -> KeyService:
    return KeyService()


def get_config_service() -> ConfigService:
    return ConfigService()


def get_docker_service() -> DockerService:
    return DockerService(get_docker_client())


def get_host_service() -> HostService:
    return HostService(get_docker_client())


def get_awg_service() -> AWGService:
    return AWGService(
        host_service=get_host_service(),
        docker_service=get_docker_service(),
        key_service=get_key_service(),
    )


__all__ = [
    "AWGService",
    "ConfigService",
    "DockerService",
    "HostService",
    "KeyService",
    "get_awg_service",
    "get_config_service",
    "get_docker_client",
    "get_docker_service",
    "get_host_service",
    "get_key_service",
]

