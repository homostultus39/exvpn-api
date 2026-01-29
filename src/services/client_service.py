from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.management.operations.client import (
    count_clients,
    create_client,
    delete_client,
    get_client_by_id,
    get_client_by_ip,
    list_clients,
    update_client_name,
)
from src.database.management.operations.server_config import get_server_config
from src.minio.client import MinIOClient
from src.services.awg_configurator import AWGService
from src.services.client_configurator import ConfigService
from src.services.key_generator import KeyService
from src.services.management.exceptions import AWGServiceError, ConfigServiceError
from src.services.management.schemas import ClientConfigData, JunkPacketConfig, ServerConfigData
from src.utils.settings import get_settings


@dataclass
class ClientConfigPayload:
    config: str
    config_key: str


class ClientService:
    def __init__(
        self,
        awg_service: AWGService,
        config_service: ConfigService,
        key_service: KeyService,
        minio_client: MinIOClient
    ):
        self._awg = awg_service
        self._config = config_service
        self._keys = key_service
        self._minio = minio_client
        self._settings = get_settings()

    async def list_clients(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> tuple[list, int]:
        clients = await list_clients(session, skip=skip, limit=limit)
        total = await count_clients(session)
        return clients, total

    async def get_client(self, session: AsyncSession, client_id: UUID):
        return await get_client_by_id(session, client_id)

    async def create_client(self, session: AsyncSession, client_name: str):
        server_config = await get_server_config(session)
        if not server_config or not server_config.server_public_key:
            raise ValueError("Server is not configured")

        if not server_config.container_name:
            raise ValueError("Server container is not configured")

        server_endpoint = self._settings.awg_server_endpoint
        if not server_endpoint:
            raise ValueError("Server endpoint is not configured")

        existing_ips = await self._awg.get_existing_peer_ips()
        next_ip = self._awg.calculate_next_ip(server_config.awg_subnet_ip, existing_ips)

        client_private_key, client_public_key = self._keys.generate_x25519_keypair()
        psk = self._keys.generate_psk()

        await self._awg.add_client_peer(client_public_key, next_ip, psk)
        await self._awg.sync_config(server_config.container_name)

        config_payload = self._generate_client_config(
            client_private_key=client_private_key,
            client_ip=next_ip,
            psk=psk,
            server_public_key=server_config.server_public_key,
            server_endpoint=server_endpoint,
            server_port=server_config.awg_server_port,
            junk_packet_config=server_config.config,
        )

        config_key = self._minio.upload_config(client_public_key, config_payload)

        try:
            return await create_client(
                session,
                client_id=client_public_key,
                client_name=client_name,
                client_private_key=client_private_key,
                client_public_key=client_public_key,
                client_ip=next_ip,
                psk_key=psk,
                config_minio_key=config_key
            )
        except Exception:
            self._minio.delete_config(config_key)
            raise

    async def update_client(self, session: AsyncSession, client_id: UUID, client_name: str):
        client = await get_client_by_id(session, client_id)
        if not client:
            return None
        return await update_client_name(session, client, client_name)

    async def delete_client(self, session: AsyncSession, client_id: UUID):
        client = await get_client_by_id(session, client_id)
        if not client:
            return None

        server_config = await get_server_config(session)
        if not server_config or not server_config.container_name:
            raise ValueError("Server is not configured")

        await self._awg.remove_client_peer(client.client_public_key)
        await self._awg.sync_config(server_config.container_name)

        if client.config_minio_key:
            self._minio.delete_config(client.config_minio_key)

        await delete_client(session, client)
        return client

    async def get_client_config(self, session: AsyncSession, client_id: UUID) -> str:
        client = await get_client_by_id(session, client_id)
        if not client or not client.config_minio_key:
            raise ValueError("Client config not found")
        return self._minio.download_config(client.config_minio_key)

    async def get_client_config_url(self, session: AsyncSession, client_id: UUID) -> str:
        client = await get_client_by_id(session, client_id)
        if not client or not client.config_minio_key:
            raise ValueError("Client config not found")
        return self._minio.get_presigned_url(client.config_minio_key)

    def _generate_client_config(
        self,
        *,
        client_private_key: str,
        client_ip: str,
        psk: str,
        server_public_key: str,
        server_endpoint: str,
        server_port: int,
        junk_packet_config: dict | None
    ) -> str:
        client_data = ClientConfigData(
            client_private_key=client_private_key,
            client_ip=client_ip,
            psk=psk
        )

        junk_config = None
        if junk_packet_config:
            junk_config = JunkPacketConfig.model_validate(junk_packet_config)

        server_data = ServerConfigData(
            server_public_key=server_public_key,
            server_endpoint=server_endpoint,
            server_port=server_port,
            junk_packet_config=junk_config
        )

        return self._config.generate_client_config(client_data, server_data)

