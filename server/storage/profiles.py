"""Public profile data; runs only on the existing SQLite worker."""
import base64
import binascii
import hashlib
import re
import struct
import unicodedata
import zlib


def initialize(db):
    db.execute('''CREATE TABLE IF NOT EXISTS profiles (
        user_id INTEGER PRIMARY KEY REFERENCES users(id), bio TEXT NOT NULL,
        color TEXT NOT NULL, avatar TEXT NOT NULL, avatar_version TEXT NOT NULL)''')
    db.commit()


def metadata(db, people):
    for person in people:
        row = db.execute('SELECT color,avatar_version FROM profiles WHERE user_id=?',
                         (person['id'],)).fetchone()
        person.update(dict(row) if row else dict(color='#5865f2', avatar_version=''))
    return people


def validate_avatar(value):
    """Accept only bounded, normalized 96px RGB PNGs, not arbitrary image files."""
    if not isinstance(value, str) or len(value) > 44000:
        raise ValueError('Profile picture is too large.')
    if not value:
        return ''
    try:
        raw = base64.b64decode(value, validate=True)
        if len(raw) > 32768 or raw[:8] != b'\x89PNG\r\n\x1a\n':
            raise ValueError()
        offset, compressed, types = 8, bytearray(), []
        while offset < len(raw):
            size = struct.unpack('!I', raw[offset:offset+4])[0]
            kind = raw[offset+4:offset+8]
            data = raw[offset+8:offset+8+size]
            crc = raw[offset+8+size:offset+12+size]
            if len(data) != size or crc != struct.pack('!I', zlib.crc32(kind+data)):
                raise ValueError()
            types.append(kind)
            if kind == b'IHDR' and data != struct.pack('!IIBBBBB', 96, 96, 8, 2, 0, 0, 0):
                raise ValueError()
            if kind == b'IDAT':
                compressed.extend(data)
            if kind not in (b'IHDR', b'IDAT', b'IEND', b'pHYs', b'sRGB', b'gAMA'):
                raise ValueError()
            if kind == b'IEND' and size:
                raise ValueError()
            offset += size + 12
        if offset != len(raw) or types.count(b'IHDR') != 1 or types[0] != b'IHDR' or types[-1] != b'IEND' or types.count(b'IEND') != 1:
            raise ValueError()
        decoder = zlib.decompressobj()
        pixels = decoder.decompress(compressed, 96 * 289 + 1)
        if len(pixels) != 96 * 289 or not decoder.eof or decoder.unused_data or any(pixels[i] > 4 for i in range(0, len(pixels), 289)):
            raise ValueError()
    except (ValueError, binascii.Error, struct.error, zlib.error, IndexError):
        raise ValueError('Choose a valid picture through the profile editor.') from None
    return hashlib.sha256(raw).hexdigest()[:16]


def dispatch(db, operation, user, payload):
    if operation == 'profile_update':
        name, bio, color = payload.get('display_name'), payload.get('bio', ''), payload.get('color', '#5865f2')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 64 or any(unicodedata.category(c).startswith('C') for c in name):
            raise ValueError('Display name must contain 1–64 characters without control characters.')
        if not isinstance(bio, str) or len(bio) > 280 or any(unicodedata.category(c).startswith('C') and c != '\n' for c in bio):
            raise ValueError('About me must be at most 280 characters.')
        if not isinstance(color, str) or not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            raise ValueError('Choose a valid banner color.')
        avatar = payload.get('avatar', '')
        version = validate_avatar(avatar)
        with db:
            db.execute('UPDATE users SET display_name=? WHERE id=?', (name.strip(), user))
            db.execute('INSERT OR REPLACE INTO profiles VALUES(?,?,?,?,?)', (user, bio.strip(), color, avatar, version))
        target = user  # Never accept an identity supplied by the client for writes.
    elif operation == 'profile_get':
        target = payload.get('user_id', user)
        if type(target) is not int or not 0 < target < 2**63:
            raise ValueError('Unknown user.')
    else:
        raise ValueError('Unknown profile operation.')
    row = db.execute('SELECT id,username,display_name FROM users WHERE id=?', (target,)).fetchone()
    if not row:
        raise ValueError('Unknown user.')
    result = dict(row)
    extra = db.execute('SELECT bio,color,avatar,avatar_version FROM profiles WHERE user_id=?', (target,)).fetchone()
    result.update(dict(extra) if extra else dict(bio='', color='#5865f2', avatar='', avatar_version=''))
    return result
