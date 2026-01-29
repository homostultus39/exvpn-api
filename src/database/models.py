import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, Enum, Integer, String, Text, UUID

from src.database.management.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )


class UUIDMixin:
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False
    )


class ServerStatus(str, PyEnum):
    NOT_CONFIGURED = "not_configured"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    ERROR = "error"



SINGLETON_SERVER_CONFIG_ID = UUID("00000000-0000-0000-0000-000000000001")


class Client(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "clients"

    client_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client_private_key: Mapped[str] = mapped_column(Text, nullable=False)
    client_public_key: Mapped[str] = mapped_column(Text, nullable=False)
    client_ip: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    psk_key: Mapped[str] = mapped_column(Text, nullable=False)
    config_minio_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ServerConfig(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "server_config"

    status: Mapped[ServerStatus] = mapped_column(
        Enum(ServerStatus),
        default=ServerStatus.NOT_CONFIGURED,
        nullable=False
    )
    awg_subnet_ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    awg_server_port: Mapped[int] = mapped_column(Integer, default=55424, nullable=False)
    server_public_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    server_private_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    psk_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    container_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
