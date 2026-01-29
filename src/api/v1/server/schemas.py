from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.database.models import ServerStatus
from src.services.management.schemas import JunkPacketConfig


class ServerSetupRequest(BaseModel):
    awg_subnet_ip: str = Field(
        default="10.8.1.0/24",
        pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$",
        description="AWG subnet in CIDR format (e.g., 10.8.1.0/24)"
    )
    awg_server_port: int = Field(
        default=55424,
        ge=1,
        le=65535,
        description="AWG server port"
    )
    junk_packet_config: Optional[JunkPacketConfig] = Field(
        default_factory=JunkPacketConfig,
        description="Junk packet configuration parameters"
    )


class ServerSetupResponse(BaseModel):
    status: str = Field(..., description="Operation status")
    server_public_key: str = Field(..., description="Server public key")
    server_private_key: str = Field(..., description="Server private key")
    psk_key: str = Field(..., description="Pre-shared key")
    awg_subnet_ip: str = Field(..., description="AWG subnet")
    awg_server_port: int = Field(..., description="AWG server port")
    container_name: str = Field(..., description="Container name")
    config: dict = Field(default_factory=dict, description="Additional configuration")


class ServerStatusResponse(BaseModel):
    status: ServerStatus = Field(..., description="Server configuration status")
    container_status: Optional[str] = Field(None, description="Docker container status")
    container_name: Optional[str] = Field(None, description="Container name")
    awg_subnet_ip: Optional[str] = Field(None, description="Current AWG subnet")
    awg_server_port: Optional[int] = Field(None, description="Current AWG server port")
    clients_count: int = Field(default=0, description="Number of active clients")
    docker_available: bool = Field(..., description="Docker availability status")


class ServerConfigResponse(BaseModel):
    id: UUID = Field(..., description="Server config ID")
    status: ServerStatus = Field(..., description="Configuration status")
    awg_subnet_ip: Optional[str] = Field(None, description="AWG subnet")
    awg_server_port: int = Field(..., description="AWG server port")
    server_public_key: Optional[str] = Field(None, description="Server public key")
    server_private_key: Optional[str] = Field(None, description="Server private key")
    psk_key: Optional[str] = Field(None, description="Pre-shared key")
    container_name: Optional[str] = Field(None, description="Container name")
    config: Optional[dict] = Field(None, description="JSONB configuration")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")

    class Config:
        from_attributes = True
