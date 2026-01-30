import base64
import collections
import json
import zlib


def decode_config(encoded_string: str) -> dict:
    encoded_data = encoded_string.replace("vpn://", "")
    padding = 4 - (len(encoded_data) % 4)
    encoded_data += "=" * padding
    compressed_data = base64.urlsafe_b64decode(encoded_data)

    try:
        original_data_len = int.from_bytes(compressed_data[:4], byteorder='big')
        decompressed_data = zlib.decompress(compressed_data[4:])

        if len(decompressed_data) != original_data_len:
            raise ValueError("Invalid length of decompressed data")

        return json.loads(decompressed_data, object_pairs_hook=collections.OrderedDict)
    except zlib.error:
        return json.loads(compressed_data.decode(), object_pairs_hook=collections.OrderedDict)


def encode_config(config: dict) -> str:
    json_str = json.dumps(config, indent=4).encode()
    compressed_data = zlib.compress(json_str)
    original_data_len = len(json_str)
    header = original_data_len.to_bytes(4, byteorder='big')
    encoded_data = base64.urlsafe_b64encode(header + compressed_data).decode().rstrip("=")
    return f"vpn://{encoded_data}"

