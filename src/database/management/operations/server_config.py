from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import ServerConfig, ServerStatus, SINGLETON_SERVER_CONFIG_ID


async def get_server_config(session: AsyncSession) -> Optional[ServerConfig]:
    """Get server configuration (singleton)"""
    result = await session.execute(
        select(ServerConfig).where(ServerConfig.id == UUID(SINGLETON_SERVER_CONFIG_ID))
    )
    return result.scalar_one_or_none()


async def get_or_create_server_config(
    session: AsyncSession,
    awg_subnet_ip: str,
    awg_server_port: int,
    server_public_key: str,
    server_private_key: str,
    psk_key: str,
    container_name: str,
    config: Optional[dict] = None
) -> ServerConfig:
    """Get or create server configuration (singleton pattern)"""
    server = await get_server_config(session)

    if server is None:
        server = ServerConfig(
            id=UUID(SINGLETON_SERVER_CONFIG_ID),
            status=ServerStatus.CONFIGURED,
            awg_subnet_ip=awg_subnet_ip,
            awg_server_port=awg_server_port,
            server_public_key=server_public_key,
            server_private_key=server_private_key,
            psk_key=psk_key,
            container_name=container_name,
            config=config or {}
        )
        session.add(server)
    else:
        server.status = ServerStatus.CONFIGURED
        server.awg_subnet_ip = awg_subnet_ip
        server.awg_server_port = awg_server_port
        server.server_public_key = server_public_key
        server.server_private_key = server_private_key
        server.psk_key = psk_key
        server.container_name = container_name
        server.config = config or {}

    await session.commit()
    await session.refresh(server)
    return server


async def update_server_status(
    session: AsyncSession,
    status: ServerStatus
) -> Optional[ServerConfig]:
    """Update server configuration status"""
    server = await get_server_config(session)

    if server is None:
        return None

    server.status = status
    await session.commit()
    await session.refresh(server)
    return server


async def get_active_clients_count(session: AsyncSession) -> int:
    """Get count of active clients"""
    from src.database.models import Client

    result = await session.execute(
        select(func.count(Client.id)).where(Client.is_active == True)
    )
    return result.scalar_one()
