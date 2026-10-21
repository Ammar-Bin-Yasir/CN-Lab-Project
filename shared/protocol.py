"""Bounded length-prefixed UTF-8 JSON control frames."""

import json
import struct

# 64 KiB maximum JSON body
MAX_FRAME = 65536

# Keep receiving until we have exactly the requested number of bytes.
def receive_exact(sock, length):
    chunks = bytearray()
    while len(chunks) < length:
        data = sock.recv(length - len(chunks))
        if not data:
            raise EOFError("Connection closed during receive.")
        chunks.extend(data)
    return bytes(chunks)

# Encode a Python message and transmit its length followed by its body.
def send_frame(sock, message):
    body = json.dumps(message, ensure_ascii=False, allow_nan=False).encode("utf-8")
    if not 0 < len(body) <= MAX_FRAME:
        raise ValueError("Control message exceeds 64 KiB.")
    sock.sendall(struct.pack("!I", len(body)) + body)


def receive_frame(sock):
    length = struct.unpack("!I", receive_exact(sock, 4))[0]
    if not 0 < length <= MAX_FRAME:
        raise ValueError("Invalid control frame length.")

    def reject_constant(value):
        raise ValueError("Non-finite JSON value.")

    try:
        message = json.loads(
            receive_exact(sock, length).decode("utf-8"), parse_constant=reject_constant
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise ValueError("Invalid JSON frame.") from error
    if not isinstance(message, dict):
        raise ValueError("A control frame must be an object.")
    return message


def request_fields(message):
    if message.get("version") != 1:
        raise ValueError("Unsupported protocol version.")
    kind, request_id, payload = (
        message.get(k) for k in ("type", "request_id", "payload")
    )
    if (
        not isinstance(kind, str)
        or len(kind) > 50
        or not isinstance(request_id, str)
        or not 1 <= len(request_id) <= 64
        or not isinstance(payload, dict)
    ):
        raise ValueError("Invalid request envelope.")
    return kind, request_id, payload
