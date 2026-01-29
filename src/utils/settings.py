from functools import lru_cache
from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    is_production: bool = Field(default=False)

    app_name: str = Field(default="ExVPN Management API")
    debug: bool = Field(default=False)
    secret_key: str = Field(...)

    postgres_host: str = Field(default="postgres")
    postgres_port: int = Field(default=5432)
    postgres_user: str = Field(...)
    postgres_password: str = Field(...)
    postgres_db: str = Field(...)

    redis_host: str = Field(default="redis")
    redis_port: int = Field(default=6379)
    redis_db: int = Field(default=0)

    minio_endpoint: str = Field(...)
    minio_access_key: str = Field(...)
    minio_secret_key: str = Field(...)
    minio_bucket_name: str = Field(default="amneziawg-configs")
    minio_use_ssl: bool = Field(default=False)

    ssh_hostname: str = Field(...)
    ssh_port: int = Field(default=22)
    ssh_username: str = Field(...)
    ssh_password: Optional[str] = Field(default=None)
    ssh_private_key_path: Optional[str] = Field(default=None)

    admin_username: str = Field(...)
    admin_password: str = Field(...)

    encryption_key: str = Field(...)

    jwt_secret_key: str = Field(...)
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=15)
    jwt_refresh_token_expire_days: int = Field(default=7)

    model_config = SettingsConfigDict(
        env_file=".env.prod",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @field_validator("ssh_password", "ssh_private_key_path")
    @classmethod
    def validate_ssh_credentials(cls, v, info):
        if info.field_name == "ssh_password" and v is None:
            if info.data.get("ssh_private_key_path") is None:
                raise ValueError(
                    "Either ssh_password or ssh_private_key_path must be provided"
                )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
