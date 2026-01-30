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
        container_name: str = "amnezia-awg",
        subnet_ip: str | None = None,
        wireguard_config: str | None = None,
        description: str | None = None,
        name_overridden_by_user: bool = True
    ) -> str:
        config_dict = self._build_config_dict(
            client_data=client_data,
            server_data=server_data,
            client_public_key=client_public_key,
            container_name=container_name,
            subnet_ip=subnet_ip,
            wireguard_config=wireguard_config,
            description=description,
            name_overridden_by_user=name_overridden_by_user
        )
        return self._create_vpn_link(config_dict)

    def _build_config_dict(
        self,
        client_data: ClientConfigData,
        server_data: ServerConfigData,
        client_public_key: str,
        container_name: str,
        subnet_ip: str | None = None,
        wireguard_config: str | None = None,
        description: str | None = None,
        name_overridden_by_user: bool = True
    ) -> dict:
        subnet_address = subnet_ip.split('/')[0] if subnet_ip else None
        
        awg_config = {}
        
        if server_data.junk_packet_config:
            junk_params = self._build_junk_params(server_data.junk_packet_config)
            awg_config.update({
                "H1": junk_params["H1"],
                "H2": junk_params["H2"],
                "H3": junk_params["H3"],
                "H4": junk_params["H4"],
                "Jc": junk_params["Jc"],
                "Jmin": junk_params["Jmin"],
                "Jmax": junk_params["Jmax"],
                "S1": junk_params["S1"],
                "S2": junk_params["S2"],
            })
        
        awg_config["port"] = str(server_data.server_port)
        awg_config["transport_proto"] = "udp"
        
        if subnet_address:
            awg_config["subnet_address"] = subnet_address
        
        if wireguard_config:
            awg_config["last_config"] = self._build_last_config(
                client_data=client_data,
                server_data=server_data,
                client_public_key=client_public_key,
                wireguard_config=wireguard_config,
                subnet_address=subnet_address
            )

        config_dict = {
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
        
        if description:
            config_dict["description"] = description
        
        if name_overridden_by_user:
            config_dict["nameOverriddenByUser"] = True

        return config_dict

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
    
    def _build_last_config(
        self,
        client_data: ClientConfigData,
        server_data: ServerConfigData,
        client_public_key: str,
        wireguard_config: str,
        subnet_address: str | None = None
    ) -> str:
        client_id = base64.b64encode(client_public_key.encode('utf-8')).decode('utf-8')
        
        last_config_dict = {}
        
        if server_data.junk_packet_config:
            junk_config = server_data.junk_packet_config
            last_config_dict.update({
                "H1": str(junk_config.h1),
                "H2": str(junk_config.h2),
                "H3": str(junk_config.h3),
                "H4": str(junk_config.h4),
                "Jc": str(junk_config.jc),
                "Jmax": str(junk_config.jmax),
                "Jmin": str(junk_config.jmin),
                "S1": str(junk_config.s1),
                "S2": str(junk_config.s2),
            })
        
        last_config_dict.update({
            "allowed_ips": ["0.0.0.0/0", "::/0"],
            "clientId": client_id,
            "client_ip": client_data.client_ip,
            "client_priv_key": client_data.client_private_key,
            "client_pub_key": client_public_key,
            "config": wireguard_config,
            "hostName": server_data.server_endpoint,
            "mtu": "1376",
            "persistent_keep_alive": "25",
            "port": server_data.server_port,
            "psk_key": client_data.psk,
            "server_pub_key": server_data.server_public_key,
        })
        
        if subnet_address:
            last_config_dict["subnet_address"] = subnet_address
        
        return json.dumps(last_config_dict, indent=4, ensure_ascii=False)

    def _create_vpn_link(self, data: dict) -> str:
        json_str = json.dumps(data, separators=(',', ':'))
        compressed = self._compress_and_encode(json_str)
        return f"vpn://{compressed}"

    def _compress_and_encode(self, json_str: str) -> str:
        json_bytes = json_str.encode('utf-8')
        uncompressed_size = len(json_bytes)
        
        compressed = zlib.compress(json_bytes, level=8)
        
        header = uncompressed_size.to_bytes(4, byteorder='big')
        data_with_header = header + compressed
        
        encoded = base64.urlsafe_b64encode(data_with_header).decode('utf-8').rstrip('=')
        return encoded
