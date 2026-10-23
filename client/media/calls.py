"""TCP authenticates call lifetime; bounded UDP datagrams carry live media."""

import select
import socket
import time
from threading import Thread, Event
from queue import Queue, Empty
from shared.protocol import send_frame, receive_frame
from shared.media import Codec, VideoFrames, fragments, HELLO, AUDIO, VIDEO, MAX_DATAGRAM
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
        self.udp = None
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
            self.sock.settimeout(10)
            if self.stop.is_set():
                return
            send_frame(self.sock, dict(token=self.token, call_id=self.call_id,
                                       transport="udp-v1"))
            response = receive_frame(self.sock)
            if not response.get("ok"):
                raise ValueError("Server rejected UDP media; update both server and client.")
            info = response["payload"]
            if info.get("transport") != "udp-v1":
                raise ValueError("This call requires the UDP version on both computers.")
            codec = Codec(bytes.fromhex(info["identity"]), bytes.fromhex(info["key"]))
            self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp.connect((self.sock.getpeername()[0], info["udp_port"]))
            self.udp.settimeout(0.2)
            deadline = time.monotonic() + 5
            next_hello = 0
            # Retry registration because the very first UDP packet can also be lost.
            while not self.stop.is_set():
                now = time.monotonic()
                if now > deadline:
                    raise TimeoutError("UDP media is unreachable. Allow UDP on the server's media port.")
                if now >= next_hello:
                    self.udp.send(codec.encode(HELLO))
                    next_hello = now + 0.5
                try:
                    packet = codec.decode(self.udp.recv(MAX_DATAGRAM + 1))
                except socket.timeout:
                    continue
                except ValueError:
                    continue
                if packet[0] == HELLO:
                    break
            if self.stop.is_set():
                return
            self.audio.start()
            self.notify("active", None)

            def send_loop():
                sequences = {AUDIO: 0, VIDEO: 0}
                next_hello = 0
                try:
                    while not self.stop.is_set():
                        now = time.monotonic()
                        if now >= next_hello:
                            self.udp.send(codec.encode(HELLO))
                            next_hello = now + 1
                        try:
                            data = self.outgoing.get(timeout=0.02)
                        except Empty:
                            continue
                        # Keep only a short capture backlog; fresh audio matters most.
                        if self.outgoing.qsize() > 4:
                            continue
                        kind = data[0]
                        frame = sequences[kind]
                        sequences[kind] += 1
                        for packet in fragments(codec, kind, frame, data[1:]):
                            self.udp.send(packet)
                except (OSError, ValueError) as exc:
                    if not self.stop.is_set():
                        self.failure(str(exc))

            writer = Thread(target=send_loop, name="chatters-media-send", daemon=True)
            writer.start()
            if self.video:
                camera = Thread(target=capture, args=(
                    self.stop, self.outgoing,
                    lambda data: self.notify("local_video", data), self.failure,
                ), daemon=True)
                camera.start()
            frames = VideoFrames()
            last_received = time.monotonic()
            while not self.stop.is_set():
                readable, _, _ = select.select([self.sock, self.udp], [], [], 0.2)
                if self.sock in readable:
                    raise ConnectionError("The server closed the media session.")
                if time.monotonic() - last_received > 10:
                    raise TimeoutError("UDP media connection was lost.")
                if self.udp not in readable:
                    continue
                try:
                    kind, frame, stamp, index, count, data = codec.decode(
                        self.udp.recv(MAX_DATAGRAM + 1))
                except ValueError:
                    continue
                last_received = time.monotonic()
                if kind == AUDIO:
                    self.audio.receive(data, frame)
                elif kind == VIDEO and self.video:
                    image = frames.add(frame, stamp, index, count, data)
                    if image is not None:
                        self.notify("remote_video", image)
        except Exception as exc:
            if not self.stop.is_set():
                self.notify("error", str(exc))
        finally:
            self.close()
            if writer:
                writer.join(2)
            try:
                self.audio.close()
            except Exception as exc:
                self.notify("error", "Audio device cleanup failed: " + str(exc))
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
        if self.udp:
            self.udp.close()
