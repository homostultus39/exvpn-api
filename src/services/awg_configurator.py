from __future__ import annotations

from dataclasses import dataclass
from ipaddress import IPv4Network

from src.services.container_manager import DockerService
from src.services.management.exceptions import (
    AWGServiceError,
    ConfigParseError,
    ContainerNotRunningError,
)
from src.services.host_files import HostService
from src.services.key_generator import KeyService
from src.services.management.ip_utils import get_next_available_ip
from src.services.management.schemas import AWGSetupParams
from src.utils.settings import get_settings


@dataclass
class ServerKeys:
    private_key: str
    public_key: str
    psk: str


class AWGService:
    def __init__(
        self,
        host_service: HostService,
        docker_service: DockerService,
        key_service: KeyService
    ):
        self._host = host_service
        self._docker = docker_service
        self._keys = key_service
        self._settings = get_settings()

    async def setup_server(self, params: AWGSetupParams) -> dict[str, str]:
        """
        Setup AWG server with validation
        Args:
            params: Validated AWG setup parameters
        Returns:
            Server configuration data
        """
        if not await self._docker.is_docker_available():
            raise AWGServiceError("Docker is not available")

        if not await self._docker.image_exists(self._settings.awg_container_image):
            await self._docker.pull_image(self._settings.awg_container_image)

        container_status = await self._docker.get_container_status(params.container_name)

        if container_status is None:
            await self._docker.create_container(
                image=self._settings.awg_container_image,
                name=params.container_name,
                detach=True,
                network_mode="host",
                cap_add=["NET_ADMIN"],
                volumes={"/opt/amnezia": {"bind": "/opt/amnezia", "mode": "rw"}},
                restart_policy={"Name": "unless-stopped"},
                devices=[
                    {
                        "PathOnHost": "/dev/net/tun",
                        "PathInContainer": "/dev/net/tun",
                        "CgroupPermissions": "rwm",
                    }
                ],
            )
            await self._docker.start_container(params.container_name)
            await self._docker.wait_for_container_ready(params.container_name)
        elif container_status == "running":
            pass
        elif container_status in ("restarting", "created"):
            await self._docker.wait_for_container_ready(params.container_name)
        else:
            await self._docker.start_container(params.container_name)
            await self._docker.wait_for_container_ready(params.container_name)

        keys = await self.generate_server_keys(params.container_name)
        server_ip, prefix = self._get_server_ip(params.awg_subnet_ip)
        config_content = self._build_server_config(
            server_private_key=keys.private_key,
            server_ip=server_ip,
            prefix=prefix,
            server_port=params.awg_server_port,
        )
        await self._host.write_file(self._settings.awg_config_path, config_content)
        await self._ensure_interface_up(params.container_name)
        await self._configure_iptables(params.container_name, params.awg_subnet_ip)

        return {
            "container_name": params.container_name,
            "server_private_key": keys.private_key,
            "server_public_key": keys.public_key,
            "psk_key": keys.psk,
            "awg_subnet_ip": params.awg_subnet_ip,
            "awg_server_port": str(params.awg_server_port),
            "config": params.junk_packet_config.model_dump() if params.junk_packet_config else {},
        }

    async def generate_server_keys(self, container_name: str) -> ServerKeys:
        """Generate server keys using wg commands in container"""
        exit_code, private_key, stderr = await self._host.exec_in_container(
            container_name,
            "wg genkey",
        )
        if exit_code != 0:
            raise AWGServiceError(f"Failed to generate server private key: {stderr}")

        private_key = private_key.strip()
        cmd = f"sh -c \"printf '%s' '{private_key}' | wg pubkey\""
        exit_code, public_key, stderr = await self._host.exec_in_container(container_name, cmd)
        if exit_code != 0:
            raise AWGServiceError(f"Failed to generate server public key: {stderr}")

        return ServerKeys(
            private_key=private_key,
            public_key=public_key.strip(),
            psk=self._keys.generate_psk(),
        )

    async def get_existing_peer_ips(self) -> list[str]:
        """Get list of existing peer IPs from config"""
        if not self._host.file_exists(self._settings.awg_config_path):
            return []
        content = await self._host.read_file(self._settings.awg_config_path)
        return self._extract_peer_ips(content)

    def calculate_next_ip(self, subnet: str, existing_ips: list[str]) -> str:
        """Calculate next available IP in subnet"""
        server_ip, _ = self._get_server_ip(subnet)
        return get_next_available_ip(subnet, existing_ips, [server_ip])

    async def add_client_peer(self, client_public_key: str, client_ip: str, psk: str) -> None:
        """Add client peer to AWG config"""
        content = await self._read_config_or_raise()
        peer_block = self._build_peer_block(client_public_key, client_ip, psk)
        updated = content.strip() + "\n\n" + peer_block + "\n"
        await self._host.write_file(self._settings.awg_config_path, updated)

    async def remove_client_peer(self, client_public_key: str) -> None:
        """Remove client peer from AWG config"""
        content = await self._read_config_or_raise()
        updated = self._remove_peer_block(content, client_public_key)
        await self._host.write_file(self._settings.awg_config_path, updated)

    async def sync_config(self, container_name: str) -> None:
        """Sync AWG configuration without restart"""
        temp_config = "/tmp/awg_sync.conf"
        command = (
            f"awg-quick strip {self._settings.awg_config_path} > {temp_config} && "
            f"awg syncconf {self._settings.awg_interface_name} {temp_config} && "
            f"rm -f {temp_config}"
        )
        exit_code, stdout, stderr = await self._host.exec_in_container(container_name, command)
        if exit_code != 0:
            error_msg = f"syncconf failed. Exit code: {exit_code}"
            if stdout.strip():
                error_msg += f", stdout: {stdout.strip()}"
            if stderr.strip():
                error_msg += f", stderr: {stderr.strip()}"
            raise AWGServiceError(error_msg)

    async def _ensure_interface_up(self, container_name: str) -> None:
        """Ensure AWG interface is up"""
        check_tun_cmd = "test -c /dev/net/tun && echo OK || echo MISSING"
        exit_code, tun_check, _ = await self._host.exec_in_container(
            container_name, check_tun_cmd
        )
        if exit_code != 0 or "MISSING" in tun_check:
            raise AWGServiceError(
                "/dev/net/tun device is not available in container. "
                "Container must be created with device mapping: /dev/net/tun:/dev/net/tun"
            )
        check_status_cmd = (
            f"ip link show {self._settings.awg_interface_name} 2>/dev/null | "
            f"grep -q 'state UP' && echo UP || echo DOWN"
        )
        exit_code, interface_status, _ = await self._host.exec_in_container(
            container_name, check_status_cmd
        )
        if "UP" in interface_status:
            return

        down_cmd = (
            f"sh -c \"awg-quick down {self._settings.awg_config_path} "
            f">/dev/null 2>&1 || true\""
        )
        await self._host.exec_in_container(container_name, down_cmd)

        up_cmd = f"sh -c \"awg-quick up {self._settings.awg_config_path} 2>&1\""
        exit_code, stdout, stderr = await self._host.exec_in_container(container_name, up_cmd)
        if exit_code == 0:
            return

        exit_code_check, status_after, _ = await self._host.exec_in_container(
            container_name, check_status_cmd
        )
        if "UP" in status_after:
            return

        error_msg = (
            f"Failed to start awg interface '{self._settings.awg_interface_name}'. "
            f"Exit code: {exit_code}\n"
            f"stdout: {stdout}\n"
            f"stderr: {stderr}"
        )
        raise ContainerNotRunningError(error_msg)

    async def _configure_iptables(self, container_name: str, subnet: str) -> None:
        """Configure iptables for AWG traffic"""
        commands = [
            f"iptables -t nat -A POSTROUTING -s {subnet} -o eth0 -j MASQUERADE",
            f"iptables -A FORWARD -i {self._settings.awg_interface_name} -j ACCEPT",
            f"iptables -A FORWARD -o {self._settings.awg_interface_name} -j ACCEPT",
        ]
        command = "sh -c \"" + " && ".join(commands) + "\""
        exit_code, _, stderr = await self._host.exec_in_container(container_name, command)
        if exit_code != 0:
            raise AWGServiceError(f"iptables configuration failed: {stderr}")

    async def _read_config_or_raise(self) -> str:
        """Read config file or raise error if not found"""
        if not self._host.file_exists(self._settings.awg_config_path):
            raise ConfigParseError(f"Config not found at {self._settings.awg_config_path}")
        return await self._host.read_file(self._settings.awg_config_path)

    def _build_server_config(
        self,
        *,
        server_private_key: str,
        server_ip: str,
        prefix: int,
        server_port: int,
    ) -> str:
        return (
            "[Interface]\n"
            f"PrivateKey = {server_private_key}\n"
            f"Address = {server_ip}/{prefix}\n"
            f"ListenPort = {server_port}\n"
        )

    def _build_peer_block(self, public_key: str, client_ip: str, psk: str) -> str:
        return (
            "[Peer]\n"
            f"PublicKey = {public_key}\n"
            f"PresharedKey = {psk}\n"
            f"AllowedIPs = {client_ip}/32\n"
        )

    def _remove_peer_block(self, content: str, public_key: str) -> str:
        sections = content.split("\n[Peer]")
        if len(sections) == 1:
            return content

        header = sections[0].strip()
        peers = ["[Peer]" + section for section in sections[1:]]

        kept_peers = []
        for peer in peers:
            if f"PublicKey = {public_key}" not in peer:
                kept_peers.append(peer.strip())

        result = header
        if kept_peers:
            result += "\n\n" + "\n\n".join(kept_peers)
        return result.strip() + "\n"

    def _extract_peer_ips(self, content: str) -> list[str]:
        ips: list[str] = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("AllowedIPs"):
                parts = line.split("=", 1)
                if len(parts) != 2:
                    continue
                ip_part = parts[1].strip().split(",", 1)[0].strip()
                ip = ip_part.split("/", 1)[0].strip()
                if ip:
                    ips.append(ip)
        return ips

    def _get_server_ip(self, subnet: str) -> tuple[str, int]:
        network = IPv4Network(subnet, strict=False)
        server_ip = next(network.hosts())
        return str(server_ip), network.prefixlen


