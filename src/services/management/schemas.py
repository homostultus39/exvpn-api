from pydantic import BaseModel, Field, field_validator


class JunkPacketConfig(BaseModel):
    """Validation model for AWG junk packet configuration"""
    jc: int = Field(default=4, ge=0, le=10, description="Junk packet count")
    jmin: int = Field(default=50, ge=0, description="Minimum junk packet size")
    jmax: int = Field(default=1000, ge=50, description="Maximum junk packet size")
    s1: int = Field(default=0, ge=0, description="Init packet junk size")
    s2: int = Field(default=0, ge=0, description="Response packet junk size")
    s3: int = Field(default=0, ge=0, description="Cookie reply packet junk size")
    s4: int = Field(default=0, ge=0, description="Transport packet junk size")
    h1: int = Field(default=1, ge=0, description="Init packet magic header")
    h2: int = Field(default=2, ge=0, description="Response packet magic header")
    h3: int = Field(default=3, ge=0, description="Underload packet magic header")
    h4: int = Field(default=4, ge=0, description="Transport packet magic header")
    i1: int = Field(default=0, ge=0, description="Special junk parameter 1")
    i2: int = Field(default=0, ge=0, description="Special junk parameter 2")
    i3: int = Field(default=0, ge=0, description="Special junk parameter 3")
    i4: int = Field(default=0, ge=0, description="Special junk parameter 4")
    i5: int = Field(default=0, ge=0, description="Special junk parameter 5")

    @field_validator("jmax")
    @classmethod
    def validate_jmax(cls, v: int, info) -> int:
        jmin = info.data.get("jmin", 50)
        if v < jmin:
            raise ValueError(f"jmax ({v}) must be >= jmin ({jmin})")
        return v


class ClientConfigData(BaseModel):
    """Validation model for client configuration data"""
    client_private_key: str = Field(..., min_length=1)
    client_ip: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    psk: str = Field(..., min_length=1)


class ServerConfigData(BaseModel):
    """Validation model for server configuration data"""
    server_public_key: str = Field(..., min_length=1)
    server_endpoint: str = Field(..., min_length=1)
    server_port: int = Field(..., ge=1, le=65535)
    primary_dns: str = Field(default="1.1.1.1", pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    secondary_dns: str = Field(default="8.8.8.8", pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
    junk_packet_config: JunkPacketConfig | None = None


class AWGSetupParams(BaseModel):
    """Validation model for AWG server setup parameters"""
    awg_subnet_ip: str = Field(..., pattern=r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/\d{1,2}$")
    awg_server_port: int = Field(..., ge=1, le=65535)
    junk_packet_config: JunkPacketConfig | None = None
    container_name: str = Field(default="amneziawg", min_length=1, max_length=255)
