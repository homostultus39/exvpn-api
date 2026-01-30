from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ClientCreateRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=255)


class ClientUpdateRequest(BaseModel):
    client_name: str = Field(..., min_length=1, max_length=255)


class ClientResponse(BaseModel):
    id: UUID
    unique_identifier: str
    client_name: str
    client_ip: str
    config_minio_key: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ClientListResponse(BaseModel):
    clients: list[ClientResponse]
    total: int


class ClientConfigResponse(BaseModel):
    config: str


class ConfigFormat(BaseModel):
    key: str = Field(..., description="Configuration key in text format")
    presigned_url: str = Field(..., description="Temporary presigned URL for download")


class ClientConfigsResponse(BaseModel):
    amnezia_app: ConfigFormat = Field(..., description="Configuration for AmneziaVPN App (vpn:// format)")
    amnezia_wg: ConfigFormat = Field(..., description="Configuration for AmneziaWG (.conf format)")

