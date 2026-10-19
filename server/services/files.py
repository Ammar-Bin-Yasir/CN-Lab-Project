"""Separate authenticated binary TCP channel for ordinary files and recordings."""

from threading import Thread, Lock, Event
import socket, hashlib, uuid, re, os
from shared.protocol import send_frame, receive_frame
from server.storage.conversations import target_parts
from .messaging import deliver

LIMIT = 20 * 1024 * 1024
CHUNK = 65536


class FileService:
    def __init__(self, server, host, port):
        self.server = server
        self.root = server.data / "files"
        self.root.mkdir(parents=True, exist_ok=True)
        self.stop = Event()
        self.lock = Lock()
        self.workers = {}
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((host, port))
        self.sock.listen(16)
        self.sock.settimeout(0.5)
        self.port = self.sock.getsockname()[1]
        self.thread = Thread(target=self.run, name="chatters-files")
        self.thread.start()

    def run(self):
        while not self.stop.is_set():
            try:
                sock, _ = self.sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            sock.settimeout(15)
            with self.lock:
                if len(self.workers) >= 8:
                    sock.close()
                    continue
                worker = Thread(target=self.handle, args=(sock,), name="chatters-file")
                self.workers[sock] = worker
            worker.start()

    def handle(self, sock):
        temp = None
        try:
            request = receive_frame(sock)
            session = self.server.registry.by_token(request.get("token"))
            if not session:
                raise ValueError("Sign in again before transferring files.")
            user = session.profile["id"]
            if request.get("op") == "upload":
                target = request.get("target")
                self.server.store.operation(
                    "authorize", user, {"target": target}
                ).result()
                kind, number = target_parts(target)
                if kind == "user" and not self.server.registry.get(number):
                    raise ValueError("Recipient is offline.")
                size = request.get("size")
                sha = request.get("sha256")
                name = request.get("name")
                if type(size) is not int or not 0 <= size <= LIMIT:
                    raise ValueError("File limit is 20 MiB.")
                if not isinstance(sha, str) or not re.fullmatch("[0-9a-f]{64}", sha):
                    raise ValueError("Invalid checksum.")
                if (
                    not isinstance(name, str)
                    or not name
                    or len(name) > 150
                    or "/" in name
                    or "\\" in name
                    or name in (".", "..")
                    or any(ord(c) < 32 for c in name)
                ):
                    raise ValueError("Invalid file name.")
                file_id = uuid.uuid4().hex
                temp = self.root / (file_id + ".part")
                send_frame(sock, {"ok": True, "payload": {"id": file_id}})
                received = 0
                hasher = hashlib.sha256()
                with temp.open("xb") as output:
                    while received < size:
                        chunk = sock.recv(min(CHUNK, size - received))
                        if not chunk:
                            raise ValueError("Upload interrupted.")
                        output.write(chunk)
                        hasher.update(chunk)
                        received += len(chunk)
                if hasher.hexdigest() != sha:
                    raise ValueError("Checksum mismatch.")
                if self.server.registry.by_token(request.get("token")) is not session:
                    raise ValueError("Session ended during upload.")
                self.server.store.operation(
                    "authorize", user, {"target": target}
                ).result()
                os.replace(temp, self.root / file_id)
                temp = None
                metadata = dict(
                    id=file_id, target=target, name=name, size=size, sha256=sha
                )
                try:
                    self.server.store.operation("file_save", user, metadata).result()
                    message = self.server.store.operation(
                        "save_message",
                        user,
                        dict(
                            target=target,
                            body=f"Attachment: {name} ({size:,} bytes)",
                            attachment=file_id,
                        ),
                    ).result()
                except Exception:
                    (self.root / file_id).unlink(missing_ok=True)
                    raise
                deliver(self.server, user, message)
                send_frame(sock, {"ok": True, "payload": metadata})
            elif request.get("op") == "download":
                metadata = self.server.store.operation(
                    "file_get", user, {"id": request.get("id")}
                ).result()
                # Only server-generated IDs can select disk paths.
                if not re.fullmatch("[0-9a-f]{32}", metadata["id"]):
                    raise ValueError("Invalid attachment ID.")
                with (self.root / metadata["id"]).open("rb") as source:
                    send_frame(sock, {"ok": True, "payload": metadata})
                    while chunk := source.read(CHUNK):
                        sock.sendall(chunk)
            else:
                raise ValueError("Unknown file operation.")
        except (OSError, EOFError, ValueError) as error:
            try:
                send_frame(sock, {"ok": False, "error": {"message": str(error)}})
            except (OSError, ValueError):
                pass
        except Exception:
            import logging

            logging.exception("File operation failed")
            try:
                send_frame(
                    sock,
                    {
                        "ok": False,
                        "error": {"message": "Server file operation failed."},
                    },
                )
            except OSError:
                pass
        finally:
            if temp:
                temp.unlink(missing_ok=True)
            sock.close()
            with self.lock:
                self.workers.pop(sock, None)

    def close(self):
        self.stop.set()
        self.sock.close()
        self.thread.join(2)
        with self.lock:
            items = list(self.workers.items())
        for sock, _ in items:
            try:
                sock.shutdown(2)
            except OSError:
                pass
        for _, worker in items:
            worker.join()
