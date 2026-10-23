"""Bounded, authenticated UDP media packets; no encryption is provided."""

import hashlib
import hmac
import struct
import time

HELLO, AUDIO, VIDEO = 0, 1, 2
MAX_DATAGRAM = 1200
HEADER = struct.Struct("!4s16sBIIIHH")
TAG_SIZE = 16
PAYLOAD_SIZE = MAX_DATAGRAM - HEADER.size - TAG_SIZE
MAX_VIDEO = 96 * 1024
MAX_PARTS = (MAX_VIDEO + PAYLOAD_SIZE - 1) // PAYLOAD_SIZE


class Codec:
    """One per endpoint; independent send counters and receive replay tracking."""

    def __init__(self, identity, key, server=False):
        if len(identity) != 16 or len(key) != 32:
            raise ValueError("Invalid media credentials.")
        # Direction labels prevent reflecting a server packet back as a client packet.
        self.send_label = b"S" if server else b"C"
        self.receive_label = b"C" if server else b"S"
        self.identity = identity
        self.key = key
        self.counter = 0
        self.highest = -1
        self.seen = 0

    def encode(self, kind, frame=0, timestamp=0, index=0, count=1, payload=b""):
        if self.counter > 0xFFFFFFFF:
            raise ValueError("Media packet counter exhausted; start a new call.")
        header = HEADER.pack(b"CHU1", self.identity, kind, self.counter,
                             frame, timestamp, index, count)
        self.counter += 1
        data = header + payload
        if len(data) + TAG_SIZE > MAX_DATAGRAM:
            raise ValueError("Media datagram is too large.")
        return data + hmac.digest(self.key, self.send_label + data, hashlib.sha256)[:TAG_SIZE]

    def decode(self, data):
        if not HEADER.size + TAG_SIZE <= len(data) <= MAX_DATAGRAM:
            raise ValueError("Invalid datagram size.")
        magic, identity, kind, counter, frame, timestamp, index, count = HEADER.unpack_from(data)
        if magic != b"CHU1" or identity != self.identity or not hmac.compare_digest(
            data[-TAG_SIZE:], hmac.digest(self.key, self.receive_label + data[:-TAG_SIZE], hashlib.sha256)[:TAG_SIZE]
        ):
            raise ValueError("Invalid media signature.")
        payload = data[HEADER.size:-TAG_SIZE]
        if kind == HELLO:
            valid = count == 1 and index == 0 and not payload
        elif kind == AUDIO:
            valid = count == 1 and index == 0 and len(payload) == 640
        elif kind == VIDEO:
            valid = (0 <= index < count <= MAX_PARTS and 0 < len(payload) <= PAYLOAD_SIZE
                     and (index == count - 1 or len(payload) == PAYLOAD_SIZE)
                     and (index != count - 1 or
                          (count - 1) * PAYLOAD_SIZE + len(payload) <= MAX_VIDEO))
        else:
            valid = False
        if not valid:
            raise ValueError("Invalid media payload.")
        if counter > self.highest:
            self.seen = ((self.seen << min(counter - self.highest, 256)) | 1) & ((1 << 256) - 1)
            self.highest = counter
        else:
            age = self.highest - counter
            if age >= 256 or self.seen & (1 << age):
                raise ValueError("Repeated or expired media packet.")
            self.seen |= 1 << age
        return kind, frame, timestamp, index, count, payload


def fragments(codec, kind, frame, payload):
    if kind == AUDIO and len(payload) != 640:
        raise ValueError("Invalid audio block.")
    if kind == VIDEO and not 0 < len(payload) <= MAX_VIDEO:
        return  # Oversized camera frames are dropped, not IP-fragmented.
    count = (len(payload) + PAYLOAD_SIZE - 1) // PAYLOAD_SIZE
    timestamp = int(time.monotonic() * 1000) & 0xFFFFFFFF
    for index in range(count):
        yield codec.encode(kind, frame, timestamp, index, count,
                           payload[index * PAYLOAD_SIZE:(index + 1) * PAYLOAD_SIZE])


class VideoFrames:
    """Reassemble at most three frames for 350 ms; incomplete frames expire."""

    def __init__(self):
        self.frames = {}
        self.last = -1

    def add(self, frame, timestamp, index, count, payload, now=None):
        now = time.monotonic() if now is None else now
        expired = [key for key, value in self.frames.items() if now - value[0] >= 0.35]
        if expired:
            self.last = max(self.last, max(expired))
        self.frames = {key: value for key, value in self.frames.items() if key > self.last}
        if frame <= self.last:
            return None
        if frame not in self.frames:
            if len(self.frames) >= 3:
                oldest = min(self.frames)
                if frame < oldest:
                    return None
                self.frames.pop(oldest)
            self.frames[frame] = (now, timestamp, count, {})
        _, stamp, parts, blocks = self.frames[frame]
        if stamp != timestamp or parts != count:
            return None
        blocks[index] = payload
        if len(blocks) == count:
            data = b"".join(blocks[i] for i in range(count))
            self.frames.pop(frame)
            if len(data) <= MAX_VIDEO:
                self.last = frame
                return data
        return None
