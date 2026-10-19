"""Custom UDP discovery; not mDNS."""

import socket
import json
from threading import Thread, Event


class DiscoveryServer:
    def __init__(self, tcp_port, port=5051):
        self.stop = Event()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("", port))
        self.sock.settimeout(0.5)
        self.tcp_port = tcp_port
        self.thread = Thread(target=self.run, name="chatters-discovery")
        self.thread.start()

    def run(self):
        while not self.stop.is_set():
            try:
                data, address = self.sock.recvfrom(1024)
                if data == b"CHATTERS_DISCOVER_1":
                    self.sock.sendto(
                        json.dumps(
                            dict(
                                service="chatters",
                                version=1,
                                name="Chatters LAN",
                                port=self.tcp_port,
                            )
                        ).encode(),
                        address,
                    )
            except socket.timeout:
                pass
            except OSError:
                break

    def close(self):
        self.stop.set()
        self.sock.close()
        self.thread.join(2)
