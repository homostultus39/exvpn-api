import base64
import json
import zlib

from src.services.management.schemas import ClientConfigData, JunkPacketConfig, ServerConfigData


class AmneziaConfigGenerator:
    def generate_amnezia_vpn_config(
        self,
        client_data: ClientConfigData,
        server_data: ServerConfigData,
        client_public_key: str,
        container_name: str = "amnezia-awg"
    ) -> str:
        config_dict = self._build_config_dict(
            client_data=client_data,
            server_data=server_data,
            client_public_key=client_public_key,
            container_name=container_name
        )
        return self._create_vpn_link(config_dict)

    def _build_config_dict(
        self,
        client_data: ClientConfigData,
        server_data: ServerConfigData,
        client_public_key: str,
        container_name: str
    ) -> dict:
        awg_config = {
            "client_priv_key": client_data.client_private_key,
            "client_pub_key": client_public_key,
            "server_pub_key": server_data.server_public_key,
            "psk_key": client_data.psk,
            "client_ip": f"{client_data.client_ip}/32",
            "allowed_ips": "0.0.0.0/0, ::/0",
            "persistent_keep_alive": "25",
        }

        if server_data.junk_packet_config:
            awg_config.update(self._build_junk_params(server_data.junk_packet_config))

        return {
            "hostName": server_data.server_endpoint,
            "defaultContainer": container_name,
            "dns1": server_data.primary_dns,
            "dns2": server_data.secondary_dns,
            "containers": [
                {
                    "container": container_name,
                    "awg": awg_config
                }
            ]
        }

    def _build_junk_params(self, junk_config: JunkPacketConfig) -> dict:
        return {
            "Jc": str(junk_config.jc),
            "Jmin": str(junk_config.jmin),
            "Jmax": str(junk_config.jmax),
            "S1": str(junk_config.s1),
            "S2": str(junk_config.s2),
            "S3": str(junk_config.s3),
            "S4": str(junk_config.s4),
            "H1": str(junk_config.h1),
            "H2": str(junk_config.h2),
            "H3": str(junk_config.h3),
            "H4": str(junk_config.h4),
            "I1": str(junk_config.i1),
            "I2": str(junk_config.i2),
            "I3": str(junk_config.i3),
            "I4": str(junk_config.i4),
            "I5": str(junk_config.i5),
        }

    def _create_vpn_link(self, data: dict) -> str:
        json_str = json.dumps(data, separators=(',', ':'))
        compressed = self._compress_and_encode(json_str)
        return f"vpn://{compressed}"

    def _compress_and_encode(self, json_str: str) -> str:
        compressed = zlib.compress(json_str.encode('utf-8'), level=8)
        encoded = base64.urlsafe_b64encode(compressed).decode('utf-8').rstrip('=')
        return encoded
