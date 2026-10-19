"""Bounded outgoing queue and background control I/O, no Qt imports."""

from queue import Queue, Empty
from threading import Thread, Event
import socket, select
from shared.protocol import send_frame, receive_frame


class ClientConnection:
    def __init__(self, host, port, callback):
        self.host = host
        self.port = port
        self.callback = callback
        self.outgoing = Queue(maxsize=128)
        self.stop = Event()
        self.sock = None
        self.thread = Thread(target=self.run, name="chatters-network", daemon=True)

    def start(self):
        self.thread.start()

    def send(self, message):
        if self.stop.is_set():
            raise ConnectionError("Disconnected.")
        self.outgoing.put_nowait(message)

    def run(self):
        try:
            sock = socket.create_connection((self.host, self.port), timeout=5)
            self.sock = sock
            sock.settimeout(5)
            if self.stop.is_set():
                return
            self.callback("connected", {})
            while not self.stop.is_set():
                for _ in range(16):
                    try:
                        message = self.outgoing.get_nowait()
                    except Empty:
                        break
                    send_frame(sock, message)
                readable, _, _ = select.select([sock], [], [], 0.1)
                if readable:
                    self.callback("message", receive_frame(sock))
        except (OSError, EOFError, ValueError) as error:
            self.callback("disconnected", {"message": str(error)})
        finally:
            self.stop.set()
            if self.sock:
                self.sock.close()

    def close(self):
        self.stop.set()
        if self.sock:
            try:
                self.sock.shutdown(2)
            except OSError:
                pass
