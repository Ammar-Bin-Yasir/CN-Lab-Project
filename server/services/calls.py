"""Independent call pairs and authenticated bounded media relay."""

import socket, struct, uuid, time
from threading import Lock, Thread, Event
from queue import Queue, Full, Empty
from shared.protocol import send_frame, receive_frame, receive_exact

MAX_PACKET = 262144


class CallService:
    def __init__(self, server, host, port):
        self.server = server
        self.lock = Lock()
        self.calls = {}
        self.reserved = {}
        self.channels = {}
        self.stop = Event()
        self.workers = {}
        self.worker_lock = Lock()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(16)
        self.sock.settimeout(0.5)
        self.port = self.sock.getsockname()[1]
        self.thread = Thread(target=self.run, name="chatters-call-relay")
        self.thread.start()

    def handle(self, session, operation, payload):
        user = session.profile["id"]
        notifications = []
        with self.lock:
            if operation == "request_call":
                peer = payload.get("recipient")
                mode = payload.get("mode")
                if (
                    type(peer) is not int
                    or peer == user
                    or not self.server.registry.get(peer)
                ):
                    raise ValueError("Recipient is unavailable.")
                if mode not in ("voice", "video"):
                    raise ValueError("Unknown call mode.")
                if user in self.reserved or peer in self.reserved:
                    raise ValueError("One of the participants is busy.")
                call = dict(
                    id=uuid.uuid4().hex,
                    caller=user,
                    recipient=peer,
                    mode=mode,
                    state="ringing",
                    created=time.monotonic(),
                )
                self.calls[call["id"]] = call
                self.reserved[user] = call["id"]
                self.reserved[peer] = call["id"]
                caller = session.profile
                notifications.append(
                    (
                        peer,
                        "call_incoming",
                        {**call, "caller_name": caller["display_name"]},
                    )
                )
            else:
                call = self.calls.get(payload.get("call_id"))
                if not call or user not in (call["caller"], call["recipient"]):
                    raise ValueError("Call not found.")
                if operation == "accept_call":
                    if user != call["recipient"] or call["state"] != "ringing":
                        raise ValueError("Call cannot be accepted.")
                    call["state"] = "active"
                    call["active_at"] = time.monotonic()
                    notifications += [
                        (p, "call_state", dict(call))
                        for p in (call["caller"], call["recipient"])
                    ]
                elif operation not in ("end_call", "reject_call"):
                    raise ValueError("Unknown call operation.")
                else:
                    pass
            result = dict(call)
        for peer, kind, data in notifications:
            connection = self.server.registry.get(peer)
            if connection:
                connection.event(kind, data)
        if operation in ("end_call", "reject_call"):
            self.end(
                call["id"], "Rejected" if operation == "reject_call" else "Call ended"
            )
        return result

    def end(self, call_id, reason):
        with self.lock:
            call = self.calls.pop(call_id, None)
            if not call:
                return
            participants = (call["caller"], call["recipient"])
            channels = []
            for user in participants:
                if self.reserved.get(user) == call_id:
                    self.reserved.pop(user, None)
                channel = self.channels.pop((call_id, user), None)
                if channel:
                    channels.append(channel)
        for channel in channels:
            try:
                channel["sock"].shutdown(2)
            except OSError:
                pass
        for user in participants:
            session = self.server.registry.get(user)
            if session:
                session.event(
                    "call_state", dict(id=call_id, state="ended", reason=reason)
                )

    def disconnect(self, user):
        with self.lock:
            call_id = self.reserved.get(user)
        if call_id:
            self.end(call_id, "Participant disconnected")

    def run(self):
        while not self.stop.is_set():
            now = time.monotonic()
            with self.lock:
                expired = [
                    c["id"]
                    for c in self.calls.values()
                    if (c["state"] == "ringing" and now - c["created"] > 30)
                    or (
                        c["state"] == "active"
                        and now - c["active_at"] > 20
                        and not all(
                            (c["id"], u) in self.channels
                            for u in (c["caller"], c["recipient"])
                        )
                    )
                ]
            for call_id in expired:
                self.end(call_id, "Call timed out")
            try:
                sock, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            sock.settimeout(15)
            with self.worker_lock:
                if len(self.workers) >= 16:
                    sock.close()
                    continue
                worker = Thread(
                    target=self.channel, args=(sock,), name="chatters-media"
                )
                self.workers[sock] = worker
            worker.start()

    def channel(self, sock):
        call_id = None
        claimed = False
        done = Event()
        writer = None
        try:
            request = receive_frame(sock)
            session = self.server.registry.by_token(request.get("token"))
            if not session:
                raise ValueError("Invalid session.")
            user = session.profile["id"]
            call_id = request.get("call_id")
            with self.lock:
                call = self.calls.get(call_id)
                if (
                    not call
                    or call["state"] != "active"
                    or user not in (call["caller"], call["recipient"])
                    or (call_id, user) in self.channels
                ):
                    raise ValueError("Media channel is not authorized.")
                peer = call["recipient"] if user == call["caller"] else call["caller"]
                channel = {"sock": sock, "queue": Queue(maxsize=16)}
                self.channels[(call_id, user)] = channel
                claimed = True
                video = call["mode"] == "video"
            send_frame(
                sock, {"ok": True, "payload": {"sample_rate": 16000, "blocksize": 320}}
            )

            def send_loop():
                try:
                    while not done.is_set():
                        try:
                            packet = channel["queue"].get(timeout=0.2)
                        except Empty:
                            continue
                        sock.sendall(struct.pack("!I", len(packet)) + packet)
                except OSError:
                    done.set()
                    try:
                        sock.shutdown(2)
                    except OSError:
                        pass

            writer = Thread(target=send_loop, name="chatters-media-writer")
            writer.start()
            while not done.is_set():
                length = struct.unpack("!I", receive_exact(sock, 4))[0]
                if not 1 < length <= MAX_PACKET:
                    raise ValueError("Invalid media packet.")
                packet = receive_exact(sock, length)
                if packet[0] == 1:
                    if len(packet) != 641:
                        raise ValueError("Invalid audio block.")
                elif packet[0] != 2 or not video:
                    raise ValueError("Invalid media type.")
                with self.lock:
                    destination = self.channels.get((call_id, peer))
                if destination:
                    try:
                        destination["queue"].put_nowait(packet)
                    except Full:
                        pass  # Drop rather than accumulating live-media delay.
        except (OSError, EOFError, ValueError):
            pass
        finally:
            done.set()
            try:
                sock.shutdown(2)
            except OSError:
                pass
            sock.close()
            if writer:
                writer.join(2)
            if claimed:
                self.end(call_id, "Media channel closed")
            with self.worker_lock:
                self.workers.pop(sock, None)

    def close(self):
        self.stop.set()
        self.sock.close()
        self.thread.join(2)
        with self.lock:
            ids = list(self.calls)
        for call_id in ids:
            self.end(call_id, "Server stopped")
        with self.worker_lock:
            items = list(self.workers.items())
        for sock, _ in items:
            try:
                sock.shutdown(2)
            except OSError:
                pass
        for _, thread in items:
            thread.join()
