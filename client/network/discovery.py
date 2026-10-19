"""Discover for a bounded interval; call from a background thread."""

import socket, json, time


def discover(port=5051):
    found = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        for host in ("255.255.255.255", "127.0.0.1"):
            try:
                sock.sendto(b"CHATTERS_DISCOVER_1", (host, port))
            except OSError:
                pass
        deadline = time.monotonic() + 1.5
        while time.monotonic() < deadline:
            try:
                data, address = sock.recvfrom(1024)
                item = json.loads(data)
                if (
                    item.get("service") == "chatters"
                    and type(item.get("port")) is int
                    and 1 <= item["port"] <= 65535
                ):
                    found[(address[0], item["port"])] = dict(
                        host=address[0],
                        port=item["port"],
                        name=str(item.get("name", "Chatters"))[:64],
                    )
            except socket.timeout:
                pass
            except (ValueError, OSError, AttributeError):
                continue
    return list(found.values())
