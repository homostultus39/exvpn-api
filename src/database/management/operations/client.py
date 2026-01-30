from uuid import UUID

from sqlalchemy import Select, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import Client


def _apply_active_filter(query: Select, include_inactive: bool) -> Select:
    if not include_inactive:
        return query.where(Client.is_active == True)
    return query


async def create_client_without_config(
    session: AsyncSession,
    *,
    unique_identifier: str,
    client_name: str,
    client_private_key: str,
    client_public_key: str,
    client_ip: str,
    psk_key: str
) -> Client:
    client = Client(
        unique_identifier=unique_identifier,
        client_name=client_name,
        client_private_key=client_private_key,
        client_public_key=client_public_key,
        client_ip=client_ip,
        psk_key=psk_key,
        config_minio_key=None,
        is_active=True
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def get_client_by_id(session: AsyncSession, client_id: UUID) -> Client | None:
    result = await session.execute(
        select(Client).where(Client.id == client_id)
    )
    return result.scalar_one_or_none()


async def get_client(
    session: AsyncSession,
    *,
    id: UUID | None = None,
    unique_identifier: str | None = None,
    client_ip: str | None = None
) -> Client | None:
    query = select(Client)

    if id is not None:
        query = query.where(Client.id == id)
    elif unique_identifier is not None:
        query = query.where(Client.unique_identifier == unique_identifier)
    elif client_ip is not None:
        query = query.where(Client.client_ip == client_ip)
    else:
        raise ValueError("At least one filter parameter must be provided")

    result = await session.execute(query)
    return result.scalar_one_or_none()


async def list_clients(
    session: AsyncSession,
    skip: int = 0,
    limit: int = 100,
    include_inactive: bool = False
) -> list[Client]:
    query = select(Client).offset(skip).limit(limit)
    query = _apply_active_filter(query, include_inactive)
    query = query.order_by(Client.created_at.desc())
    result = await session.execute(query)
    return list(result.scalars().all())


async def count_clients(
    session: AsyncSession,
    include_inactive: bool = False
) -> int:
    query = select(func.count(Client.id))
    query = _apply_active_filter(query, include_inactive)
    result = await session.execute(query)
    return int(result.scalar_one())


async def create_client(
    session: AsyncSession,
    *,
    client_id: str,
    client_name: str,
    client_private_key: str,
    client_public_key: str,
    client_ip: str,
    psk_key: str,
    config_minio_key: str | None
) -> Client:
    client = Client(
        client_id=client_id,
        client_name=client_name,
        client_private_key=client_private_key,
        client_public_key=client_public_key,
        client_ip=client_ip,
        psk_key=psk_key,
        config_minio_key=config_minio_key,
        is_active=True
    )
    session.add(client)
    await session.commit()
    await session.refresh(client)
    return client


async def update_client_name(
    session: AsyncSession,
    client: Client,
    client_name: str
) -> Client:
    client.client_name = client_name
    await session.commit()
    await session.refresh(client)
    return client


async def update_client_config_key(
    session: AsyncSession,
    client: Client,
    config_minio_key: str
) -> Client:
    client.config_minio_key = config_minio_key
    await session.commit()
    await session.refresh(client)
    return client


async def update_client_active_status(
    session: AsyncSession,
    client: Client,
    is_active: bool
) -> Client:
    client.is_active = is_active
    await session.commit()
    await session.refresh(client)
    return client


async def deactivate_client(session: AsyncSession, client: Client) -> None:
    client.is_active = False
    await session.commit()


async def delete_client(session: AsyncSession, client: Client) -> None:
    await session.delete(client)
    await session.commit()

