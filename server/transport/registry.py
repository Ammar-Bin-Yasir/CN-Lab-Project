"""Live sessions; never hold the registry lock during socket I/O."""

from threading import Lock


class Registry:
    def __init__(self):
        self.lock = Lock()
        self.sessions = {}

    def bind(self, connection, profile):
        with self.lock:
            if profile["id"] in self.sessions:
                raise ValueError(
                    "This account is already online. Sign out on the other device first."
                )
            connection.profile = profile
            self.sessions[profile["id"]] = connection

    def remove(self, connection):
        with self.lock:
            if (
                connection.profile
                and self.sessions.get(connection.profile["id"]) is connection
            ):
                del self.sessions[connection.profile["id"]]

    def online(self):
        with self.lock:
            return list(self.sessions)

    def get(self, user):
        with self.lock:
            return self.sessions.get(user)

    def by_token(self, token):
        import hmac

        if not isinstance(token, str) or len(token) > 128:
            return None
        with self.lock:
            return next(
                (
                    c
                    for c in self.sessions.values()
                    if hmac.compare_digest(c.token, token)
                ),
                None,
            )

    def broadcast(self, kind, payload):
        with self.lock:
            connections = list(self.sessions.values())
        for connection in connections:
            connection.event(kind, payload)
