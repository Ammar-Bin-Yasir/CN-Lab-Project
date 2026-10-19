"""Account verification followed by atomic live-session binding."""


def authenticate(server, connection, kind, payload):
    if connection.profile:
        raise ValueError("Already signed in.")
    if kind == "register":
        profile = server.store.register(
            payload.get("username"),
            payload.get("display_name", ""),
            payload.get("password"),
        ).result()
    else:
        profile = server.store.authenticate(
            payload.get("username"), payload.get("password")
        ).result()
    server.registry.bind(connection, profile)
    return {
        "profile": profile,
        "token": connection.token,
        "file_port": server.files.port,
        "media_port": server.calls.port,
    }
