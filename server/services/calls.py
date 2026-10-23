"""Independent call pairs and authenticated bounded media relay."""

import socket, uuid, time, secrets
from threading import Lock, Thread, Event
from shared.protocol import send_frame, receive_frame
from shared.media import Codec, HEADER, HELLO, VIDEO, MAX_DATAGRAM


class CallService:
    def __init__(self, server, host, port):
        self.server = server
        self.lock = Lock()
        self.calls = {}
        self.reserved = {}
        self.channels = {}
        self.identities = {}
        self.stop = Event()
        self.workers = {}
        self.worker_lock = Lock()
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(16)
        self.sock.settimeout(0.5)
        self.port = self.sock.getsockname()[1]
        self.udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.udp.bind((host, self.port))
            self.udp.settimeout(0.2)
        except Exception:
            self.udp.close()
            self.sock.close()
            raise
        self.udp_thread = Thread(target=self.relay, name="chatters-udp-relay")
        self.udp_thread.start()
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
                    self.identities.pop(channel["codec"].identity, None)
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
                            self.channels.get((c["id"], u), {}).get("address")
                            for u in (c["caller"], c["recipient"])
                        )
                    )
                    or any(now - ch["last_seen"] > 10
                           for (cid, _), ch in self.channels.items()
                           if cid == c["id"] and ch["address"] is not None)
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
        try:
            request = receive_frame(sock)
            session = self.server.registry.by_token(request.get("token"))
            if not session or request.get("transport") != "udp-v1":
                raise ValueError("Invalid session or media transport.")
            user = session.profile["id"]
            call_id = request.get("call_id")
            with self.lock:
                call = self.calls.get(call_id)
                if (
                    not call or call["state"] != "active"
                    or user not in (call["caller"], call["recipient"])
                    or (call_id, user) in self.channels
                ):
                    raise ValueError("Media channel is not authorized.")
                peer = call["recipient"] if user == call["caller"] else call["caller"]
                codec = Codec(secrets.token_bytes(16), secrets.token_bytes(32), server=True)
                channel = dict(sock=sock, codec=codec, call_id=call_id, peer=peer,
                               ip=sock.getpeername()[0], address=None,
                               video=call["mode"] == "video", last_seen=time.monotonic(),
                               budget=128000., budget_at=time.monotonic(), ack_at=-1.)
                self.channels[(call_id, user)] = channel
                self.identities[codec.identity] = channel
                claimed = True
            send_frame(sock, {"ok": True, "payload": dict(
                transport="udp-v1", udp_port=self.port, identity=codec.identity.hex(),
                key=codec.key.hex(), sample_rate=16000, blocksize=320,
            )})
            # TCP stays open only for authenticated lifetime/teardown, never media.
            sock.settimeout(0.5)
            while not self.stop.is_set():
                try:
                    sock.recv(1)
                    break
                except socket.timeout:
                    continue
        except (OSError, EOFError, ValueError, TypeError):
            pass
        finally:
            try:
                sock.shutdown(2)
            except OSError:
                pass
            sock.close()
            if claimed:
                self.end(call_id, "Media session closed")
            with self.worker_lock:
                self.workers.pop(sock, None)

    def relay(self):
        while not self.stop.is_set():
            try:
                data, address = self.udp.recvfrom(MAX_DATAGRAM + 1)
            except socket.timeout:
                continue
            except OSError:
                if self.stop.is_set():
                    break
                continue
            if not HEADER.size + 16 <= len(data) <= MAX_DATAGRAM:
                continue
            identity = data[4:20]
            with self.lock:
                channel = self.identities.get(identity)
                if not channel or channel["ip"] != address[0]:
                    continue
                if channel["address"] is not None and channel["address"] != address:
                    continue
                now = time.monotonic()
                channel["budget"] = min(128000., channel["budget"] +
                                         (now - channel["budget_at"]) * 512000)
                channel["budget_at"] = now
                if channel["budget"] < len(data):
                    continue
                channel["budget"] -= len(data)
                try:
                    packet = channel["codec"].decode(data)
                except ValueError:
                    continue
                kind, frame, stamp, index, count, payload = packet
                if kind == VIDEO and not channel["video"]:
                    continue
                if channel["address"] is None:
                    if kind != HELLO:
                        continue
                    channel["address"] = address
                channel["last_seen"] = now
                destination = None
                outgoing = None
                if kind == HELLO:
                    if now - channel["ack_at"] >= 0.3:
                        channel["ack_at"] = now
                        outgoing = channel["codec"].encode(HELLO)
                        destination = address
                else:
                    peer = self.channels.get((channel["call_id"], channel["peer"]))
                    if peer and peer["address"]:
                        outgoing = peer["codec"].encode(kind, frame, stamp, index, count, payload)
                        destination = peer["address"]
            if outgoing is not None:
                try:
                    self.udp.sendto(outgoing, destination)
                except OSError:
                    pass  # A dropped datagram must not terminate other calls.

    def close(self):
        self.stop.set()
        self.sock.close()
        self.udp.close()
        self.thread.join(2)
        self.udp_thread.join(2)
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
