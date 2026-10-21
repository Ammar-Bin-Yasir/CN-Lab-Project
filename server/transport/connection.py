"""One control worker per connected client, with serialized writes."""

import logging
import secrets
from threading import Lock
from queue import Full
from shared.protocol import receive_frame, send_frame, request_fields
from server.services import auth, groups, messaging


class Connection:
    def __init__(self, server, sock):
        self.server = server
        self.sock = sock
        self.profile = None
        self.token = secrets.token_urlsafe(32)
        self.write_lock = Lock()
        self.closed = False
        sock.settimeout(45)

    def send(self, message):
        with self.write_lock:
            if self.closed:
                return
            try:
                send_frame(self.sock, message)
            except (OSError, ValueError):
                self.close()

    def event(self, kind, payload):
        self.send(dict(version=1, type=kind, payload=payload))

    def dispatch(self, kind, payload):
        if kind in ("register", "login"):
            return auth.authenticate(self.server, self, kind, payload)
        if not self.profile:
            raise ValueError("Please sign in first.")

        user = self.profile["id"]
        if kind == "ping":
            return {}
        if kind in ("profile_get", "profile_update"):
            result = self.server.store.operation(kind, user, payload).result()
            if kind == "profile_update":
                self.profile = {key: result[key] for key in ("id", "username", "display_name")}
                self.server.registry.broadcast("refresh", {"profile_id": user})
            return result
        if kind == "snapshot":
            return {
                **self.server.store.operation("snapshot", user, {}).result(),
                "online": self.server.registry.online(),
            }
        if kind in ("history", "members"):
            return self.server.store.operation(kind, user, payload).result()
        if kind in ("create_group", "join_group", "leave_group"):
            result = groups.handle(self.server, self, kind, payload)
            self.server.registry.broadcast("refresh", {})
            return result
        if kind == "send_message":
            return messaging.send(self.server, self, payload)
        if kind in ("request_call", "accept_call", "reject_call", "end_call"):
            return self.server.calls.handle(self, kind, payload)
        raise ValueError("This operation is not implemented.")

    def run(self):
        try:
            while not self.closed:
                message = receive_frame(self.sock)
                kind, request_id, payload = request_fields(message)
                try:
                    result = self.dispatch(kind, payload)
                    self.send(
                        dict(
                            version=1,
                            type=kind,
                            request_id=request_id,
                            ok=True,
                            payload=result,
                        )
                    )
                    if kind in ("register", "login"):
                        self.server.registry.broadcast("refresh", {})
                except (ValueError, Full) as error:
                    self.send(
                        dict(
                            version=1,
                            type=kind,
                            request_id=request_id,
                            ok=False,
                            error=dict(
                                code="REQUEST_REJECTED",
                                message=str(error) or "Server is busy.",
                            ),
                        )
                    )
                except Exception:
                    logging.exception("Request failed: %s", kind)
                    self.send(
                        dict(
                            version=1,
                            type=kind,
                            request_id=request_id,
                            ok=False,
                            error=dict(
                                code="SERVER_ERROR",
                                message="Server could not complete the request.",
                            ),
                        )
                    )
        except (OSError, EOFError, ValueError):
            pass
        finally:
            self.close()
            if self.profile:
                self.server.calls.disconnect(self.profile["id"])
            self.server.registry.remove(self)
            self.server.registry.broadcast("refresh", {})
            self.server.finished(self)

    def close(self):
        self.closed = True
        try:
            self.sock.shutdown(2)
        except OSError:
            pass
        self.sock.close()
