from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.dependencies.auth import CurrentUser
from src.api.v1.dependencies.services import get_awg_service, get_docker_service
from src.api.v1.server import schemas
from src.api.v1.server.exception import (
    DockerUnavailableError,
    ServerConfigurationError,
    ServerNotConfiguredError
)
from src.database.connection import get_session
from src.database.management.operations.server_config import (
    get_active_clients_count,
    get_or_create_server_config,
    get_server_config
)
from src.database.models import ServerStatus
from src.services.awg_configurator import AWGService
from src.services.container_manager import DockerService
from src.services.management.exceptions import AWGServiceError, DockerServiceError
from src.services.management.schemas import AWGSetupParams
from src.utils.settings import get_settings

router = APIRouter()
settings = get_settings()


@router.post("/setup", response_model=schemas.ServerSetupResponse)
async def setup_server(
    request: schemas.ServerSetupRequest,
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    awg_service: Annotated[AWGService, Depends(get_awg_service)],
    docker_service: Annotated[DockerService, Depends(get_docker_service)]
):
    """
    Setup AmneziaWG server with full configuration

    - Checks Docker availability
    - Creates and starts AWG container
    - Generates server keys
    - Configures network and iptables
    - Saves configuration to database
    """
    try:
        if not await docker_service.is_docker_available():
            raise DockerUnavailableError("Docker is not available on this server")

        params = AWGSetupParams(
            awg_subnet_ip=request.awg_subnet_ip,
            awg_server_port=request.awg_server_port,
            junk_packet_config=request.junk_packet_config,
            container_name=settings.awg_container_name
        )

        setup_result = await awg_service.setup_server(params)

        await get_or_create_server_config(
            session=session,
            awg_subnet_ip=setup_result["awg_subnet_ip"],
            awg_server_port=int(setup_result["awg_server_port"]),
            server_public_key=setup_result["server_public_key"],
            server_private_key=setup_result["server_private_key"],
            psk_key=setup_result["psk_key"],
            container_name=setup_result["container_name"],
            config=setup_result["config"]
        )

        return schemas.ServerSetupResponse(
            status="success",
            server_public_key=setup_result["server_public_key"],
            server_private_key=setup_result["server_private_key"],
            psk_key=setup_result["psk_key"],
            awg_subnet_ip=setup_result["awg_subnet_ip"],
            awg_server_port=int(setup_result["awg_server_port"]),
            container_name=setup_result["container_name"],
            config=setup_result["config"]
        )

    except DockerUnavailableError:
        raise
    except (AWGServiceError, DockerServiceError) as exc:
        raise ServerConfigurationError(f"Server setup failed: {str(exc)}")
    except Exception as exc:
        raise ServerConfigurationError(f"Unexpected error during server setup: {str(exc)}")


@router.get("/status", response_model=schemas.ServerStatusResponse)
async def get_server_status(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)],
    docker_service: Annotated[DockerService, Depends(get_docker_service)]
):
    """
    Get current server status

    Returns:
    - Server configuration status
    - Docker container status
    - Number of active clients
    - Docker availability
    """
    try:
        server_config = await get_server_config(session)
        docker_available = await docker_service.is_docker_available()

        container_status = None
        container_name = None

        if server_config and docker_available and server_config.container_name:
            container_status = await docker_service.get_container_status(
                server_config.container_name
            )
            container_name = server_config.container_name

        clients_count = await get_active_clients_count(session)

        return schemas.ServerStatusResponse(
            status=server_config.status if server_config else ServerStatus.NOT_CONFIGURED,
            container_status=container_status,
            container_name=container_name,
            awg_subnet_ip=server_config.awg_subnet_ip if server_config else None,
            awg_server_port=server_config.awg_server_port if server_config else None,
            clients_count=clients_count,
            docker_available=docker_available
        )

    except Exception as exc:
        raise ServerConfigurationError(f"Failed to get server status: {str(exc)}")


@router.get("/config", response_model=schemas.ServerConfigResponse)
async def get_server_configuration(
    current_user: CurrentUser,
    session: Annotated[AsyncSession, Depends(get_session)]
):
    """
    Get full server configuration

    Returns complete server configuration including keys and settings
    """
    try:
        server_config = await get_server_config(session)

        if not server_config:
            raise ServerNotConfiguredError(
                "Server is not configured yet. Please use POST /server/setup first"
            )

        return schemas.ServerConfigResponse.model_validate(server_config)

    except ServerNotConfiguredError:
        raise
    except Exception as exc:
        raise ServerConfigurationError(f"Failed to get server config: {str(exc)}")
