"""TCP accept loop and orderly worker shutdown."""

import socket
from threading import Thread, Lock, Event
from pathlib import Path
from server.storage import AccountStore
from .registry import Registry
from .connection import Connection


class ChatServer:
    def __init__(self, host="0.0.0.0", port=5050, data="runtime"):
        self.data = Path(data)
        self.store = None
        self.registry = Registry()
        self.stopping = Event()
        self.lock = Lock()
        self.connections = {}
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.store = AccountStore(self.data / "server.sqlite")
            self.sock.bind((host, port))
            self.sock.listen(32)
            self.sock.settimeout(0.5)
        except Exception:
            self.sock.close()
            if self.store:
                self.store.close()
            raise
        self.port = self.sock.getsockname()[1]
        from server.services.files import FileService

        try:
            self.files = FileService(self, host, port + 1 if port else 0)
        except Exception:
            self.sock.close()
            self.store.close()
            raise
        from server.services.calls import CallService

        try:
            self.calls = CallService(self, host, port + 2 if port else 0)
        except Exception:
            self.files.close()
            self.sock.close()
            self.store.close()
            raise
        self.thread = None

    def start(self):
        self.thread = Thread(target=self.serve, name="chatters-listener")
        self.thread.start()
        return self

    def serve(self):
        while not self.stopping.is_set():
            try:
                sock, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            connection = Connection(self, sock)
            worker = Thread(target=connection.run, name="chatters-client")
            with self.lock:
                if len(self.connections) >= 32:
                    connection.close()
                    continue
                self.connections[connection] = worker
            worker.start()

    def finished(self, connection):
        with self.lock:
            self.connections.pop(connection, None)

    def close(self):
        self.stopping.set()
        self.sock.close()
        if self.thread:
            self.thread.join(3)
        with self.lock:
            items = list(self.connections.items())
        for connection, _ in items:
            connection.close()
        for _, worker in items:
            worker.join()
        self.calls.close()
        self.files.close()
        self.store.close()
