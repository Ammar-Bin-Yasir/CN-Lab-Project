"""Local preview storage. Replace this adapter with the team's network client.

No sockets, presence discovery, server authentication or delivery are simulated.
Synthetic people are explicitly preview contacts. SQLite here is preview-only.
"""
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime
from pathlib import Path

PEOPLE = {'abdullah': 'Abdullah', 'ashna': 'Ashna', 'ayesha': 'Ayesha'}


def digest(password, salt):
    return hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()


class DemoService:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.executescript('''
            CREATE TABLE IF NOT EXISTS profiles(username TEXT PRIMARY KEY, name TEXT, salt TEXT, hash TEXT);
            CREATE TABLE IF NOT EXISTS groups(id INTEGER PRIMARY KEY, name TEXT, salt TEXT, hash TEXT);
            CREATE TABLE IF NOT EXISTS members(username TEXT, group_id INTEGER, UNIQUE(username, group_id));
            CREATE TABLE IF NOT EXISTS messages(id INTEGER PRIMARY KEY, owner TEXT, target TEXT, sender TEXT, body TEXT, time TEXT);
        ''')
        self.user = None
        self.name = ''

    def register(self, username, name, password):
        username = username.strip().lower()
        if not username or not username.isascii() or not username.replace('_', '').isalnum():
            raise ValueError('Use letters, numbers and underscores for your username.')
        if len(password) < 8:
            raise ValueError('Use at least 8 characters for your preview password.')
        salt = secrets.token_hex(16)
        try:
            with self.db:
                self.db.execute('INSERT INTO profiles VALUES(?,?,?,?)', (username, name.strip() or username, salt, digest(password, salt)))
        except sqlite3.IntegrityError:
            raise ValueError('That username is already used on this preview.') from None
        self.login(username, password)

    def login(self, username, password):
        row = self.db.execute('SELECT * FROM profiles WHERE username=?', (username.strip().lower(),)).fetchone()
        if not row or not hmac.compare_digest(row[3], digest(password, row[2])):
            raise ValueError('Username or password is incorrect.')
        self.user, self.name = row[0], row[1]

    def preview(self):
        self.user, self.name = '__preview__', 'Ammar'

    def groups(self, joined=False):
        rows = self.db.execute('SELECT id,name,salt FROM groups ORDER BY id').fetchall()
        memberships = {r[0] for r in self.db.execute('SELECT group_id FROM members WHERE username=?', (self.user,))}
        return [dict(id=r[0], name=r[1], protected=bool(r[2]), joined=r[0] in memberships) for r in rows if not joined or r[0] in memberships]

    def create_group(self, name, password=''):
        if not name.strip() or len(name.strip()) > 40:
            raise ValueError('Choose a group name between 1 and 40 characters.')
        salt = secrets.token_hex(16) if password else ''
        with self.db:
            cursor = self.db.execute('INSERT INTO groups(name,salt,hash) VALUES(?,?,?)', (name.strip(), salt, digest(password, salt) if salt else ''))
            group_id = cursor.lastrowid
            self.db.execute('INSERT INTO members VALUES(?,?)', (self.user, group_id))
        return group_id

    def join(self, group_id, password=''):
        row = self.db.execute('SELECT salt,hash FROM groups WHERE id=?', (group_id,)).fetchone()
        if not row:
            raise ValueError('This group no longer exists.')
        if self.is_member(group_id):
            return
        if row[0] and not hmac.compare_digest(row[1], digest(password, row[0])):
            raise ValueError('Incorrect group password. Please try again.')
        with self.db:
            self.db.execute('INSERT OR IGNORE INTO members VALUES(?,?)', (self.user, group_id))

    def is_member(self, group_id):
        return bool(self.db.execute('SELECT 1 FROM members WHERE username=? AND group_id=?', (self.user, group_id)).fetchone())

    def leave(self, group_id):
        with self.db:
            self.db.execute('DELETE FROM members WHERE username=? AND group_id=?', (self.user, group_id))

    def check_target(self, target):
        if target.startswith('group:'):
            if not self.is_member(int(target.split(':')[1])):
                raise ValueError('Join this group before viewing or writing messages.')
        elif target not in PEOPLE:
            raise ValueError('Unknown preview contact.')

    def history(self, target):
        self.check_target(target)
        owner = '*' if target.startswith('group:') else self.user
        return self.db.execute('SELECT sender,body,time FROM messages WHERE owner=? AND target=? ORDER BY id', (owner, target)).fetchall()

    def send(self, target, body):
        self.check_target(target)
        if not body.strip() or len(body) > 4000:
            raise ValueError('Write a message between 1 and 4,000 characters.')
        owner = '*' if target.startswith('group:') else self.user
        with self.db:
            self.db.execute('INSERT INTO messages(owner,target,sender,body,time) VALUES(?,?,?,?,?)', (owner, target, self.name, body.strip(), datetime.now().strftime('%H:%M')))

    def conversations(self):
        return [r[0] for r in self.db.execute("SELECT target FROM messages WHERE owner=? AND target NOT LIKE 'group:%' GROUP BY target ORDER BY MAX(id) DESC", (self.user,))]

    def close(self):
        self.db.close()
