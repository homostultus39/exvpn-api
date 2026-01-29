from minio import Minio

from src.utils.settings import get_settings

settings = get_settings()

minio_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_use_ssl
)


def get_minio() -> Minio:
    return minio_client
