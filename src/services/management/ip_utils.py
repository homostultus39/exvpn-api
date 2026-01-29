from ipaddress import IPv4Address, IPv4Network


def parse_cidr(cidr: str) -> tuple[str, int]:
    network = IPv4Network(cidr, strict=False)
    return str(network.network_address), network.prefixlen


def get_network_address(ip: str, prefix: int) -> str:
    network = IPv4Network(f"{ip}/{prefix}", strict=False)
    return str(network.network_address)


def ip_to_int(ip: str) -> int:
    return int(IPv4Address(ip))


def int_to_ip(ip_int: int) -> str:
    return str(IPv4Address(ip_int))


def is_ip_in_subnet(ip: str, subnet: str) -> bool:
    network = IPv4Network(subnet, strict=False)
    return IPv4Address(ip) in network


def validate_ip(ip: str) -> bool:
    try:
        IPv4Address(ip)
        return True
    except ValueError:
        return False


def get_next_available_ip(subnet: str, existing_ips: list[str]) -> str:
    network = IPv4Network(subnet, strict=False)
    existing = {IPv4Address(ip) for ip in existing_ips if validate_ip(ip)}
    for ip in network.hosts():
        if ip not in existing:
            return str(ip)
    raise ValueError("No available IPs in subnet")

