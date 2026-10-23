"""Raw 16 kHz mono audio; three-block (60 ms) UDP playout buffer."""

from queue import Full
from threading import Lock
import time


class JitterBuffer:
    def __init__(self):
        self.lock = Lock()
        self.blocks = {}
        self.next = None
        self.ready_at = 0
        self.last_received = 0

    def put(self, sequence, block):
        if len(block) != 640:
            return
        now = time.monotonic()
        with self.lock:
            if self.next is None or now - self.last_received > 0.3:
                self.blocks.clear()
                self.next = sequence
                self.ready_at = now + 0.06
            self.last_received = now
            # Large gaps reset playout instead of playing obsolete buffered audio.
            if sequence > self.next + 8:
                self.blocks.clear()
                self.next = sequence
                self.ready_at = now + 0.06
            if sequence >= self.next and len(self.blocks) < 9:
                self.blocks[sequence] = block

    def take(self):
        silence = b"\0" * 640
        with self.lock:
            if self.next is None or time.monotonic() < self.ready_at:
                return silence
            block = self.blocks.pop(self.next, silence)
            self.next += 1
            return block


class AudioDevice:
    def __init__(self, outgoing):
        self.outgoing = outgoing
        self.playback = JitterBuffer()
        self.muted = False
        self.stream = None

    def start(self):
        import sounddevice as sd

        def callback(indata, outdata, frames, time, status):
            audio = b"\0" * len(indata) if self.muted else bytes(indata)
            try:
                self.outgoing.put_nowait(b"\x01" + audio)
            except Full:
                pass
            data = self.playback.take()
            outdata[:] = data if len(data) == len(outdata) else b"\0" * len(outdata)

        self.stream = sd.RawStream(
            samplerate=16000, blocksize=320, channels=1, dtype="int16", callback=callback,
        )
        self.stream.start()

    def receive(self, block, sequence):
        self.playback.put(sequence, block)

    def close(self):
        if self.stream:
            try:
                self.stream.stop()
            finally:
                self.stream.close()
