from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.database.management.operations.client import (
    count_clients,
    create_client_without_config,
    delete_client,
    get_client_by_id,
    list_clients,
    update_client_config_key,
    update_client_name,
)
from src.database.management.operations.server_config import get_server_config
from src.database.models import ServerConfig
from src.minio.client import MinIOClient
from src.services.awg_configurator import AWGService
from src.services.client_configurator import ConfigService
from src.services.key_generator import KeyService
from src.services.management.exceptions import (
    AWGServiceError,
    ClientNotFoundServiceError,
    ConfigServiceError,
    ServerNotConfiguredServiceError,
)
from src.services.management.schemas import ClientConfigData, JunkPacketConfig, ServerConfigData
from src.utils.settings import get_settings


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
        client = await get_client_by_id(session, client_id)
        if not client:
            raise ClientNotFoundServiceError(f"Client with id {client_id} not found")
        return client

    async def create_client(self, session: AsyncSession, client_name: str):
        server_config = self._ensure_server_configured(await get_server_config(session))

        server_endpoint = self._settings.awg_server_endpoint
        if not server_endpoint:
            raise ServerNotConfiguredServiceError("Server endpoint is not configured")

        existing_ips = await self._awg.get_existing_peer_ips()
        next_ip = self._awg.calculate_next_ip(server_config.awg_subnet_ip, existing_ips)

        client_private_key, client_public_key = self._keys.generate_x25519_keypair()
        psk = self._keys.generate_psk()

        client = await create_client_without_config(
            session,
            unique_identifier=client_public_key,
            client_name=client_name,
            client_private_key=client_private_key,
            client_public_key=client_public_key,
            client_ip=next_ip,
            psk_key=psk
        )

        try:
            await self._awg.add_client_peer(client_public_key, next_ip, psk)
        except Exception:
            await delete_client(session, client)
            raise

        try:
            await self._awg.sync_config(server_config.container_name)
        except Exception:
            await self._rollback_awg_peer(client_public_key)
            await delete_client(session, client)
            raise

        try:
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
        except Exception:
            await self._rollback_awg_peer(client_public_key)
            await self._awg.sync_config(server_config.container_name)
            await delete_client(session, client)
            raise

        try:
            return await update_client_config_key(session, client, config_key)
        except Exception:
            self._minio.delete_config(config_key)
            await self._rollback_awg_peer(client_public_key)
            await self._awg.sync_config(server_config.container_name)
            await delete_client(session, client)
            raise

    async def update_client(self, session: AsyncSession, client_id: UUID, client_name: str):
        client = await get_client_by_id(session, client_id)
        if not client:
            raise ClientNotFoundServiceError(f"Client with id {client_id} not found")
        return await update_client_name(session, client, client_name)

    async def delete_client(self, session: AsyncSession, client_id: UUID):
        client = await get_client_by_id(session, client_id)
        if not client:
            raise ClientNotFoundServiceError(f"Client with id {client_id} not found")

        server_config = self._ensure_server_configured(await get_server_config(session))

        errors = []

        try:
            await self._awg.remove_client_peer(client.client_public_key)
        except Exception as e:
            errors.append(f"Failed to remove AWG peer: {str(e)}")

        try:
            await self._awg.sync_config(server_config.container_name)
        except Exception as e:
            errors.append(f"Failed to sync AWG config: {str(e)}")

        if client.config_minio_key:
            try:
                self._minio.delete_config(client.config_minio_key)
            except Exception as e:
                errors.append(f"Failed to delete MinIO config: {str(e)}")

        await delete_client(session, client)

        if errors:
            raise AWGServiceError(f"Client deleted but cleanup had errors: {'; '.join(errors)}")

        return client

    async def get_client_config(self, session: AsyncSession, client_id: UUID) -> str:
        client = await self._get_client_with_config(session, client_id)
        return self._minio.download_config(client.config_minio_key)

    async def get_client_config_url(self, session: AsyncSession, client_id: UUID) -> str:
        client = await self._get_client_with_config(session, client_id)
        return self._minio.get_presigned_url(client.config_minio_key)

    def _ensure_server_configured(self, server_config: ServerConfig | None) -> ServerConfig:
        if not server_config:
            raise ServerNotConfiguredServiceError("Server is not configured")
        if not server_config.server_public_key:
            raise ServerNotConfiguredServiceError("Server public key is not configured")
        if not server_config.container_name:
            raise ServerNotConfiguredServiceError("Server container is not configured")
        return server_config

    async def _get_client_with_config(self, session: AsyncSession, client_id: UUID):
        client = await get_client_by_id(session, client_id)
        if not client:
            raise ClientNotFoundServiceError(f"Client with id {client_id} not found")
        if not client.config_minio_key:
            raise ClientNotFoundServiceError("Client configuration not found in storage")
        return client

    async def _rollback_awg_peer(self, client_public_key: str) -> None:
        try:
            await self._awg.remove_client_peer(client_public_key)
        except Exception:
            pass

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

