from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.database.models import ServerStatus


class JunkPacketConfig(BaseModel):
    jc: int = Field(default=4, description="Junk packet count")
    jmin: int = Field(default=50, description="Junk packet min size")
    jmax: int = Field(default=1000, description="Junk packet max size")
    s1: int = Field(default=0, description="Init packet junk size")
    s2: int = Field(default=0, description="Response packet junk size")
    h1: int = Field(default=1, description="Init packet magic header")
    h2: int = Field(default=2, description="Response packet magic header")
    h3: int = Field(default=3, description="Underload packet magic header")
    h4: int = Field(default=4, description="Transport packet magic header")


class ServerSetupRequest(BaseModel):
    awg_subnet_ip: str = Field(..., description="Subnet IP for clients (e.g., 10.8.1.0/24)")
    awg_server_port: int = Field(default=55424, ge=1, le=65535)
    junk_packet_config: Optional[JunkPacketConfig] = Field(default=None)


class ServerSetupResponse(BaseModel):
    status: str
    message: str


class ServerStatusResponse(BaseModel):
    status: ServerStatus
    container_status: Optional[str] = None
    clients_count: int


class ServerConfigResponse(BaseModel):
    id: UUID
    status: ServerStatus
    awg_subnet_ip: Optional[str]
    awg_server_port: int
    server_public_key: Optional[str]
    container_name: Optional[str]
    config: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
