"""Run the real Chatters server; clients connect to --port over the LAN."""

import argparse, logging, time, sqlite3
from server.transport.listener import ChatServer
from server.transport.discovery import DiscoveryServer


def main():
    parser = argparse.ArgumentParser(description="Chatters LAN server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--data", default="runtime")
    parser.add_argument("--no-discovery", action="store_true")

    args = parser.parse_args()
    if not 0 <= args.port <= 65533:
        parser.error("Choose a port from 1 to 65533, or 0 for automatic allocation.")
    logging.basicConfig(level=logging.INFO)
    try:
        server = ChatServer(args.host, args.port, args.data).start()
    except (OSError, sqlite3.Error) as error:
        parser.exit(1, f"Cannot start Chatters server: {error}\n")
    discovery = None
    try:
        if not args.no_discovery:
            try:
                discovery = DiscoveryServer(server.port)
            except OSError as error:
                logging.warning(
                    "Discovery unavailable; use manual connection: %s", error
                )
        print(f"Chatters server listening on {args.host}:{server.port}", flush=True)

        while True:
            time.sleep(0.5)

    except KeyboardInterrupt:
        pass

    finally:
        if discovery:
            discovery.close()
        server.close()


if __name__ == "__main__":
    main()
