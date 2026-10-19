"""Client live-media transport. Audio/camera work never runs on the GUI thread."""

import socket, struct
from threading import Thread, Event
from queue import Queue, Empty
from shared.protocol import send_frame, receive_frame, receive_exact
from .audio import AudioDevice
from .video import capture


class MediaCall:
    def __init__(self, host, port, token, call_id, video, notify):
        self.host = host
        self.port = port
        self.token = token
        self.call_id = call_id
        self.video = video
        self.notify = notify
        self.stop = Event()
        self.outgoing = Queue(maxsize=16)
        self.audio = AudioDevice(self.outgoing)
        self.sock = None
        self.thread = Thread(target=self.run, name="chatters-live-media", daemon=True)

    def start(self):
        self.thread.start()

    def mute(self, value):
        self.audio.muted = value

    def failure(self, message):
        self.notify("error", message)
        self.close()

    def run(self):
        writer = None
        camera = None
        try:
            self.sock = socket.create_connection((self.host, self.port), timeout=10)
            self.sock.settimeout(15)
            if self.stop.is_set():
                return
            send_frame(self.sock, dict(token=self.token, call_id=self.call_id))
            response = receive_frame(self.sock)
            if not response.get("ok"):
                raise ValueError("Server rejected media channel.")
            self.audio.start()
            self.notify("active", None)

            def send_loop():
                try:
                    while not self.stop.is_set():
                        try:
                            data = self.outgoing.get(timeout=0.2)
                        except Empty:
                            continue
                        self.sock.sendall(struct.pack("!I", len(data)) + data)
                except OSError as exc:
                    if not self.stop.is_set():
                        self.failure(str(exc))

            writer = Thread(target=send_loop, name="chatters-media-send", daemon=True)
            writer.start()
            if self.video:
                camera = Thread(
                    target=capture,
                    args=(
                        self.stop,
                        self.outgoing,
                        lambda data: self.notify("local_video", data),
                        self.failure,
                    ),
                    daemon=True,
                )
                camera.start()
            while not self.stop.is_set():
                size = struct.unpack("!I", receive_exact(self.sock, 4))[0]
                if not 1 < size <= 262144:
                    raise ValueError("Invalid media packet.")
                packet = receive_exact(self.sock, size)
                if packet[0] == 1:
                    self.audio.receive(packet[1:])
                elif packet[0] == 2 and self.video:
                    self.notify("remote_video", packet[1:])
                else:
                    raise ValueError("Unexpected media packet.")
        except Exception as exc:
            if not self.stop.is_set():
                self.notify("error", str(exc))
        finally:
            self.close()
            if writer:
                writer.join(2)
            self.audio.close()
            if camera:
                camera.join(2)
            self.notify("ended", None)

    def close(self):
        self.stop.set()
        if self.sock:
            try:
                self.sock.shutdown(2)
            except OSError:
                pass
            self.sock.close()
