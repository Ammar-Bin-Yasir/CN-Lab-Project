"""Account operations serialized through a single SQLite-owning worker.

Callers receive Futures. Transport workers may wait for results; GUI handlers
must use their network adapter instead. This is storage, not a login session.
"""

from concurrent.futures import Future
import hashlib
import hmac
from pathlib import Path
from queue import Queue
import re
import secrets
import sqlite3
from threading import Lock, Thread
import unicodedata


def _password_hash(password, salt):
    return hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)


def _username(value):
    if not isinstance(value, str):
        raise ValueError("Username must be text.")
    value = unicodedata.normalize("NFKC", value).strip().lower()
    if not re.fullmatch(r"[a-z0-9_]{3,32}", value):
        raise ValueError("Username must contain 3–32 letters, numbers or underscores.")
    return value


def _password(value):
    if not isinstance(value, str) or not 8 <= len(value) <= 128:
        raise ValueError("Password must contain 8–128 characters.")
    return value


class AccountStore:
    def __init__(self, path):
        self._path = Path(path)
        self._jobs = Queue(maxsize=128)
        self._lock = Lock()
        self._closed = False
        self._ready = Future()
        self._worker = Thread(target=self._run, name="chatters-database")
        self._worker.start()
        self._ready.result()

    def operation(self, operation, user, payload):
        return self._submit(operation, user, payload)

    def register(self, username, display_name, password):
        """Return Future[{id, username, display_name}]; ValueError on bad input/duplicate."""
        return self._submit("register", username, display_name, password)

    def authenticate(self, username, password):
        """Return a public profile after verification; does not create a session."""
        return self._submit("authenticate", username, password)

    def _submit(self, operation, *args):
        with self._lock:
            if self._closed:
                raise RuntimeError("Account storage is closed.")
            future = Future()
            # Bounded backlog: caller handles queue.Full rather than unbounded growth.
            self._jobs.put_nowait((future, operation, args))
            return future

    def _run(self):
        db = None
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self._path)
            db.row_factory = sqlite3.Row
            db.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL
            )""")
            db.commit()
            from .conversations import initialize

            initialize(db)
            from .attachments import initialize as initialize_files

            initialize_files(db)
            # Same-cost verification for unknown usernames; never persist this record.
            dummy_salt = secrets.token_bytes(16)
            dummy_hash = _password_hash("unused-dummy-password", dummy_salt)
        except Exception as error:
            if db is not None:
                db.close()
            self._ready.set_exception(error)
            return
        self._ready.set_result(None)
        try:
            while True:
                job = self._jobs.get()
                if job is None:
                    break
                future, operation, args = job
                if not future.set_running_or_notify_cancel():
                    continue
                try:
                    if operation == "register":
                        result = self._register(db, *args)
                    elif operation == "authenticate":
                        result = self._authenticate(db, dummy_salt, dummy_hash, *args)
                    elif operation.startswith("file_"):
                        from .attachments import dispatch

                        result = dispatch(db, operation, *args)
                    else:
                        from .conversations import dispatch

                        result = dispatch(db, operation, *args)
                except Exception as error:
                    future.set_exception(error)
                else:
                    future.set_result(result)
        finally:
            db.close()

    @staticmethod
    def _register(db, username, display_name, password):
        username = _username(username)
        password = _password(password)
        if not isinstance(display_name, str):
            raise ValueError("Display name must be text.")
        display_name = display_name.strip() or username
        if len(display_name) > 64 or any(
            unicodedata.category(c).startswith("C") for c in display_name
        ):
            raise ValueError(
                "Display name must be at most 64 characters without control characters."
            )
        salt = secrets.token_bytes(16)
        password_hash = _password_hash(password, salt)
        try:
            with db:
                cursor = db.execute(
                    "INSERT INTO users(username,display_name,salt,password_hash) VALUES(?,?,?,?)",
                    (username, display_name, salt, password_hash),
                )
        except sqlite3.IntegrityError:
            raise ValueError("Username is already taken.") from None
        return dict(id=cursor.lastrowid, username=username, display_name=display_name)

    @staticmethod
    def _authenticate(db, dummy_salt, dummy_hash, username, password):
        username = _username(username)
        password = _password(password)
        row = db.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        salt = row["salt"] if row else dummy_salt
        expected = row["password_hash"] if row else dummy_hash
        matches = hmac.compare_digest(_password_hash(password, salt), expected)
        if not row or not matches:
            raise ValueError("Username or password is incorrect.")
        return dict(
            id=row["id"], username=row["username"], display_name=row["display_name"]
        )

    def close(self):
        """Drain accepted jobs and close the connection. Call off the GUI thread."""
        with self._lock:
            if not self._closed:
                self._closed = True
                self._jobs.put(None)
        self._worker.join()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
