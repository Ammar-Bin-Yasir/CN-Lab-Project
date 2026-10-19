"""Qt bridge: worker callbacks become queued signals; widgets stay on GUI thread."""

import time, uuid
from queue import Full
from PySide6.QtCore import QObject, Signal, QTimer, Qt
from .connection import ClientConnection


class NetworkAdapter(QObject):
    incoming = Signal(int, str, object)
    connected = Signal()
    disconnected = Signal(str)
    server_event = Signal(str, object)

    def __init__(self):
        super().__init__()
        self.connection = None
        self.generation = 0
        self.pending = {}
        self.incoming.connect(self._receive, Qt.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)
        self.profile = None
        self.token = None
        self.last_ping = 0
        self.ready = False

    def connect_server(self, host, port):
        self.close()
        self.generation += 1
        gen = self.generation
        self.host = host
        self.port = port
        self.connection = ClientConnection(
            host, port, lambda kind, data: self.incoming.emit(gen, kind, data)
        )
        self.connection.start()

    def request(self, kind, payload, callback):
        if not self.ready:
            callback(False, {"message": "Not connected. Connect and sign in again."})
            return
        request_id = uuid.uuid4().hex
        self.pending[request_id] = (time.monotonic() + 20, callback)
        try:
            self.connection.send(
                dict(version=1, type=kind, request_id=request_id, payload=payload)
            )
        except (ConnectionError, Full):
            self.pending.pop(request_id, None)
            callback(False, {"message": "Disconnected or outgoing queue full."})

    def _receive(self, generation, kind, data):
        if generation != self.generation:
            return
        if kind == "connected":
            self.ready = True
            self.connected.emit()
            return
        if kind == "disconnected":
            self.ready = False
            self.profile = None
            self.token = None
            pending = list(self.pending.values())
            self.pending.clear()
            for _, callback in pending:
                callback(
                    False,
                    {
                        "message": "Connection lost. Request outcome may be uncertain; check history after reconnecting."
                    },
                )
            self.disconnected.emit(data.get("message", "Connection lost."))
            return
        request_id = data.get("request_id")
        if request_id:
            item = self.pending.pop(request_id, None)
            if item:
                item[1](
                    bool(data.get("ok")),
                    data.get("payload")
                    if data.get("ok")
                    else data.get("error", {"message": "Request failed."}),
                )
        else:
            self.server_event.emit(data.get("type", ""), data.get("payload", {}))

    def _tick(self):
        now = time.monotonic()
        expired = [key for key, (deadline, _) in self.pending.items() if deadline < now]
        for key in expired:
            _, callback = self.pending.pop(key)
            callback(
                False,
                {"message": "Server timed out. Check history before retrying a write."},
            )
        if self.ready and self.profile and now - self.last_ping > 10:
            self.last_ping = now
            self.request("ping", {}, lambda *_: None)

    def close(self):
        self.generation += 1
        self.ready = False
        self.profile = None
        self.token = None
        if self.connection:
            self.connection.close()
        pending = list(self.pending.values())
        self.pending.clear()
        for _, callback in pending:
            callback(False, {"message": "Connection closed."})
