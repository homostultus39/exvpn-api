from functools import lru_cache
from pathlib import Path

from src.services.management.exceptions import ConfigServiceError
from src.services.management.schemas import ClientConfigData, JunkPacketConfig, ServerConfigData


class ConfigService:
    def __init__(self, template_path: Path | None = None):
        self._template_path = template_path or self._default_template_path()

    def generate_client_config(
        self,
        client_data: ClientConfigData,
        server_data: ServerConfigData
    ) -> str:
        """
        Generate client config from validated Pydantic models
        Args:
            client_data: Validated client configuration data
            server_data: Validated server configuration data
        Returns:
            Formatted client configuration string
        """
        try:
            template = self._load_template()
            variables = self._build_variables(client_data, server_data)
            return template.format(**variables).strip() + "\n"
        except Exception as exc:
            raise ConfigServiceError(str(exc)) from exc

    def _build_variables(
        self,
        client_data: ClientConfigData,
        server_data: ServerConfigData
    ) -> dict[str, str | int]:
        """Build template variables from Pydantic models"""
        junk_config = server_data.junk_packet_config or JunkPacketConfig()

        return {
            "client_private_key": client_data.client_private_key,
            "client_ip": client_data.client_ip,
            "psk": client_data.psk,
            "server_public_key": server_data.server_public_key,
            "server_endpoint": server_data.server_endpoint,
            "server_port": str(server_data.server_port),
            "primary_dns": server_data.primary_dns,
            "secondary_dns": server_data.secondary_dns,
            "junk_packet_count": junk_config.jc,
            "junk_packet_min_size": junk_config.jmin,
            "junk_packet_max_size": junk_config.jmax,
            "init_packet_junk_size": junk_config.s1,
            "response_packet_junk_size": junk_config.s2,
            "cookie_reply_packet_junk_size": junk_config.s3,
            "transport_packet_junk_size": junk_config.s4,
            "init_packet_magic_header": junk_config.h1,
            "response_packet_magic_header": junk_config.h2,
            "underload_packet_magic_header": junk_config.h3,
            "transport_packet_magic_header": junk_config.h4,
            "special_junk_1": junk_config.i1,
            "special_junk_2": junk_config.i2,
            "special_junk_3": junk_config.i3,
            "special_junk_4": junk_config.i4,
            "special_junk_5": junk_config.i5,
        }

    @lru_cache
    def _load_template(self) -> str:
        """Load and cache template file"""
        try:
            return self._template_path.read_text(encoding="utf-8")
        except Exception as exc:
            raise ConfigServiceError(str(exc)) from exc

    @staticmethod
    def _default_template_path() -> Path:
        """Get default template path"""
        return Path(__file__).resolve().parent / "management" / "templates" / "awg_client_template.conf"

