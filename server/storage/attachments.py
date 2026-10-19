"""Attachment metadata on the same SQLite worker as accounts/messages."""

from .conversations import authorize


def initialize(db):
    db.execute("""CREATE TABLE IF NOT EXISTS attachments(
      id TEXT PRIMARY KEY, sender INTEGER NOT NULL REFERENCES users(id), target TEXT NOT NULL,
      name TEXT NOT NULL, size INTEGER NOT NULL, sha256 TEXT NOT NULL)""")
    db.commit()


def dispatch(db, operation, user, payload):
    if operation == "file_save":
        authorize(db, user, payload["target"])
        with db:
            db.execute(
                "INSERT INTO attachments VALUES(?,?,?,?,?,?)",
                (
                    payload["id"],
                    user,
                    payload["target"],
                    payload["name"],
                    payload["size"],
                    payload["sha256"],
                ),
            )
        return payload
    if operation == "file_get":
        row = db.execute(
            "SELECT * FROM attachments WHERE id=?", (payload.get("id"),)
        ).fetchone()
        if not row:
            raise ValueError("Attachment not found.")
        target = row["target"]
        if target.startswith("group:"):
            authorize(db, user, target)
        elif user not in (row["sender"], int(target.split(":")[1])):
            raise ValueError("Attachment access denied.")
        return dict(row)
    raise ValueError("Unknown attachment operation.")
