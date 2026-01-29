import base64
import secrets

from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption, PublicFormat

from src.services.management.exceptions import AWGServiceError


class KeyService:
    def generate_x25519_keypair(self) -> tuple[str, str]:
        """Generate X25519 keypair for AWG"""
        try:
            private_key = X25519PrivateKey.generate()
            public_key = private_key.public_key()

            private_bytes = private_key.private_bytes(
                encoding=Encoding.Raw,
                format=PrivateFormat.Raw,
                encryption_algorithm=NoEncryption()
            )
            public_bytes = public_key.public_bytes(
                encoding=Encoding.Raw,
                format=PublicFormat.Raw
            )

            return (
                base64.b64encode(private_bytes).decode("ascii"),
                base64.b64encode(public_bytes).decode("ascii")
            )
        except Exception as exc:
            raise AWGServiceError(f"Failed to generate X25519 keypair: {str(exc)}") from exc

    def generate_psk(self) -> str:
        """Generate pre-shared key for AWG"""
        try:
            return base64.b64encode(secrets.token_bytes(32)).decode("ascii")
        except Exception as exc:
            raise AWGServiceError(f"Failed to generate PSK: {str(exc)}") from exc

