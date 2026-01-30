from datetime import timedelta
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from src.minio.connection import get_minio
from src.utils.settings import get_settings

settings = get_settings()


class MinIOClient:
    def __init__(self, minio: Minio):
        self.minio = minio
        self.bucket_name = settings.minio_bucket_name

    def ensure_bucket_exists(self) -> None:
        try:
            if not self.minio.bucket_exists(self.bucket_name):
                self.minio.make_bucket(self.bucket_name)
        except S3Error as e:
            raise Exception(f"Failed to ensure bucket exists: {str(e)}")

    def upload_config(self, unique_identifier: str, config_content: str) -> str:
        config_key = f"configs/{unique_identifier}.conf"
        try:
            config_bytes = config_content.encode('utf-8')
            config_stream = BytesIO(config_bytes)

            self.minio.put_object(
                self.bucket_name,
                config_key,
                config_stream,
                length=len(config_bytes),
                content_type="text/plain"
            )
            return config_key
        except S3Error as e:
            raise Exception(f"Failed to upload config: {str(e)}")

    def download_config(self, config_key: str) -> str:
        try:
            response = self.minio.get_object(self.bucket_name, config_key)
            config_content = response.read().decode('utf-8')
            response.close()
            response.release_conn()
            return config_content
        except S3Error as e:
            raise Exception(f"Failed to download config: {str(e)}")

    def delete_config(self, config_key: str) -> None:
        try:
            self.minio.remove_object(self.bucket_name, config_key)
        except S3Error as e:
            raise Exception(f"Failed to delete config: {str(e)}")

    def get_presigned_url(self, config_key: str, expires_in: int = 3600) -> str:
        try:
            url = self.minio.presigned_get_object(
                self.bucket_name,
                config_key,
                expires=timedelta(seconds=expires_in)
            )
            return url
        except S3Error as e:
            raise Exception(f"Failed to generate presigned URL: {str(e)}")


def get_minio_client() -> MinIOClient:
    return MinIOClient(get_minio())
