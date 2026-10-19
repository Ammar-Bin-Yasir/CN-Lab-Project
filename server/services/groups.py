"""Group operations use the authenticated session and persistent worker."""


def handle(server, connection, kind, payload):
    return server.store.operation(kind, connection.profile["id"], payload).result()
