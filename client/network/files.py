"""Blocking binary-channel helpers; callers must use a background thread."""

import hashlib, socket, uuid, os
from pathlib import Path
from shared.protocol import send_frame, receive_frame

LIMIT = 20 * 1024 * 1024
CHUNK = 65536


def checked_response(sock):
    response = receive_frame(sock)
    if not response.get("ok"):
        raise ValueError(response.get("error", {}).get("message", "Transfer failed."))
    return response["payload"]


def upload(host, port, token, target, path, progress=lambda *_: None):
    path = Path(path)
    size = path.stat().st_size
    if not 0 <= size <= LIMIT:
        raise ValueError("File limit is 20 MiB.")
    with path.open("rb") as source:
        digest = hashlib.sha256()
        while chunk := source.read(CHUNK):
            digest.update(chunk)
        source.seek(0)
        with socket.create_connection((host, port), timeout=10) as sock:
            sock.settimeout(20)
            send_frame(
                sock,
                dict(
                    op="upload",
                    token=token,
                    target=target,
                    name=path.name,
                    size=size,
                    sha256=digest.hexdigest(),
                ),
            )
            checked_response(sock)
            sent = 0
            while sent < size:
                chunk = source.read(min(CHUNK, size - sent))
                if not chunk:
                    raise ValueError("File changed during upload.")
                sock.sendall(chunk)
                sent += len(chunk)
                progress(sent, size)
            return checked_response(sock)


def download(host, port, token, file_id, path, progress=lambda *_: None):
    path = Path(path)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".part")
    try:
        with socket.create_connection((host, port), timeout=10) as sock:
            sock.settimeout(20)
            send_frame(sock, dict(op="download", token=token, id=file_id))
            metadata = checked_response(sock)
            size = metadata["size"]
            if type(size) is not int or not 0 <= size <= LIMIT:
                raise ValueError("Invalid attachment size.")
            received = 0
            digest = hashlib.sha256()
            with temp.open("xb") as output:
                while received < size:
                    chunk = sock.recv(min(CHUNK, size - received))
                    if not chunk:
                        raise ValueError("Download interrupted.")
                    output.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    progress(received, size)
            if digest.hexdigest() != metadata["sha256"]:
                raise ValueError("Checksum mismatch.")
        os.replace(temp, path)
        return str(path)
    finally:
        temp.unlink(missing_ok=True)
