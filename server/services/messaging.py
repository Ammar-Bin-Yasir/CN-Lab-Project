"""Persist first, then route to authorized participants."""

from server.storage.conversations import target_parts


def send(server, connection, payload):
    user = connection.profile["id"]
    # No client-selected sender or attachment identity is accepted here.
    message = server.store.operation(
        "save_message",
        user,
        {"target": payload.get("target"), "body": payload.get("body")},
    ).result()
    deliver(server, user, message)
    return message


def deliver(server, user, message):
    kind, number = target_parts(message["target"])
    if kind == "group":
        members = server.store.operation(
            "members", user, {"target": message["target"]}
        ).result()
        for member in members:
            if member["id"] == user:
                continue
            peer = server.registry.get(member["id"])
            if peer:
                peer.event("message_received", message)
    else:
        peer = server.registry.get(number)
        if peer:
            peer.event("message_received", {**message, "target": f"user:{user}"})
    server.registry.broadcast("refresh", {})
