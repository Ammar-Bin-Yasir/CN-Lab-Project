"""Executed only by AccountStore's single database worker."""

from datetime import datetime, timezone
import re


def initialize(db):
    db.execute("PRAGMA foreign_keys=ON")
    db.executescript("""
      CREATE TABLE IF NOT EXISTS rooms(id INTEGER PRIMARY KEY, name TEXT NOT NULL, salt BLOB, password_hash BLOB);
      CREATE TABLE IF NOT EXISTS memberships(user_id INTEGER REFERENCES users(id), room_id INTEGER REFERENCES rooms(id), PRIMARY KEY(user_id,room_id));
      CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, sender INTEGER NOT NULL REFERENCES users(id), recipient INTEGER REFERENCES users(id), room INTEGER REFERENCES rooms(id), body TEXT NOT NULL, created TEXT NOT NULL, attachment TEXT, CHECK ((recipient IS NULL) != (room IS NULL)));
      CREATE INDEX IF NOT EXISTS message_room ON messages(room,id);
      CREATE INDEX IF NOT EXISTS message_direct ON messages(sender,recipient,id);
    """)


def target_parts(target):
    if not isinstance(target, str) or not re.fullmatch(
        r"(user|group):[1-9][0-9]{0,15}", target
    ):
        raise ValueError("Invalid conversation target.")

    kind, number = target.split(":")
    return kind, int(number)


def authorize(db, user, target):
    kind, number = target_parts(target)
    if kind == "group":
        if not db.execute(
            "SELECT 1 FROM memberships WHERE user_id=? AND room_id=?", (user, number)
        ).fetchone():
            raise ValueError("You are not a member of this group.")
    elif (
        number == user
        or not db.execute("SELECT 1 FROM users WHERE id=?", (number,)).fetchone()
    ):
        raise ValueError("Unknown recipient.")
    return kind, number


def dispatch(db, operation, user, payload):
    # Imported here to avoid a module-import cycle with the worker.
    from .accounts import _password_hash
    import secrets
    import hmac

    if operation == "snapshot":
        people = [
            dict(r)
            for r in db.execute(
                "SELECT id,username,display_name FROM users WHERE id!=? ORDER BY display_name",
                (user,),
            )
        ]
        groups = [
            dict(r)
            for r in db.execute(
                """SELECT r.id,r.name,(r.salt IS NOT NULL) protected,
          EXISTS(SELECT 1 FROM memberships m WHERE m.room_id=r.id AND m.user_id=?) joined FROM rooms r ORDER BY r.id""",
                (user,),
            )
        ]
        conversations = [
            f"user:{r[0]}"
            for r in db.execute(
                """SELECT CASE WHEN sender=? THEN recipient ELSE sender END peer,MAX(id) latest
          FROM messages WHERE room IS NULL AND (sender=? OR recipient=?) GROUP BY peer ORDER BY latest DESC""",
                (user, user, user),
            )
        ]
        return dict(people=people, groups=groups, conversations=conversations)
    if operation == "create_group":
        name, password = payload.get("name"), payload.get("password", "")
        if (
            not isinstance(name, str)
            or not 1 <= len(name.strip()) <= 40
            or not isinstance(password, str)
            or len(password) > 128
        ):
            raise ValueError(
                "Choose a group name of 1–40 characters and password up to 128 characters."
            )
        salt = secrets.token_bytes(16) if password else None
        with db:
            cursor = db.execute(
                "INSERT INTO rooms(name,salt,password_hash) VALUES(?,?,?)",
                (name.strip(), salt, _password_hash(password, salt) if salt else None),
            )
            db.execute("INSERT INTO memberships VALUES(?,?)", (user, cursor.lastrowid))
        return {"target": f"group:{cursor.lastrowid}"}
    if operation in ("join_group", "leave_group", "members"):
        kind, number = target_parts(payload.get("target"))
        if kind != "group":
            raise ValueError("Select a group.")
        room = db.execute("SELECT * FROM rooms WHERE id=?", (number,)).fetchone()
        if not room:
            raise ValueError("Group does not exist.")
        member = bool(
            db.execute(
                "SELECT 1 FROM memberships WHERE user_id=? AND room_id=?",
                (user, number),
            ).fetchone()
        )
        if operation == "members":
            if not member:
                raise ValueError("Join the group first.")
            return [
                dict(r)
                for r in db.execute(
                    "SELECT u.id,u.username,u.display_name FROM users u JOIN memberships m ON m.user_id=u.id WHERE m.room_id=?",
                    (number,),
                )
            ]
        with db:
            if operation == "leave_group":
                db.execute(
                    "DELETE FROM memberships WHERE user_id=? AND room_id=?",
                    (user, number),
                )
            elif not member:
                password = payload.get("password", "")
                if not isinstance(password, str) or len(password) > 128:
                    raise ValueError("Invalid group password.")
                if room["salt"] and not hmac.compare_digest(
                    _password_hash(password, room["salt"]), room["password_hash"]
                ):
                    raise ValueError("Incorrect group password.")
                db.execute("INSERT INTO memberships VALUES(?,?)", (user, number))
        return {"target": f"group:{number}"}
    if operation in ("history", "save_message", "authorize"):
        target = payload.get("target")
        kind, number = authorize(db, user, target)
        if operation == "authorize":
            return dict(kind=kind, id=number)
        if operation == "save_message":
            body = payload.get("body")
            if not isinstance(body, str) or not 1 <= len(body.strip()) <= 4000:
                raise ValueError("Write a message of 1–4,000 characters.")
            created = datetime.now(timezone.utc).isoformat()
            with db:
                cur = db.execute(
                    "INSERT INTO messages(sender,recipient,room,body,created,attachment) VALUES(?,?,?,?,?,?)",
                    (
                        user,
                        number if kind == "user" else None,
                        number if kind == "group" else None,
                        body.strip(),
                        created,
                        payload.get("attachment"),
                    ),
                )
            sender = db.execute(
                "SELECT display_name FROM users WHERE id=?", (user,)
            ).fetchone()[0]
            return dict(
                id=cur.lastrowid,
                sender_id=user,
                sender=sender,
                body=body.strip(),
                created=created,
                target=target,
                attachment=payload.get("attachment"),
            )
        if kind == "group":
            where = "m.room=?"
            args = (number,)
        else:
            where = "((m.sender=? AND m.recipient=?) OR (m.sender=? AND m.recipient=?))"
            args = (user, number, number, user)
        rows = db.execute(
            f"""SELECT m.id,m.sender sender_id,u.display_name sender,m.body,m.created,m.attachment,a.name attachment_name FROM messages m JOIN users u ON u.id=m.sender LEFT JOIN attachments a ON a.id=m.attachment WHERE {where} ORDER BY m.id DESC LIMIT 50""",
            args,
        ).fetchall()
        # Keep a response below the control-frame cap even with long messages.
        import json

        recent = []
        size = 0
        for row in rows:
            item = dict(row)
            cost = len(json.dumps(item, ensure_ascii=False).encode("utf-8")) + 2
            if size + cost > 48000:
                break
            recent.append(item)
            size += cost
        return list(reversed(recent))
    raise ValueError("Unknown storage operation.")
