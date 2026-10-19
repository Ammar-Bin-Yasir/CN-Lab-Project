"""Bounded microphone recording to WAV; start/finish must run off GUI thread."""

from threading import Lock
import wave


class Recorder:
    def __init__(self):
        self.lock = Lock()
        self.frames = []
        self.count = 0
        self.stream = None

    def start(self):
        import sounddevice as sd

        def callback(data, frames, time, status):
            with self.lock:
                remaining = 16000 * 60 - self.count
                if remaining > 0:
                    accepted = min(frames, remaining)
                    self.frames.append(bytes(data)[: accepted * 2])
                    self.count += accepted

        self.stream = sd.RawInputStream(
            samplerate=16000,
            blocksize=320,
            channels=1,
            dtype="int16",
            callback=callback,
        )
        self.stream.start()

    def finish(self, path=None):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if path:
            with self.lock:
                data = b"".join(self.frames)
            if not data:
                raise ValueError("No audio was recorded.")
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(16000)
                output.writeframes(data)
        self.frames.clear()


def play(path):
    import sounddevice as sd

    with wave.open(str(path), "rb") as source:
        if (
            source.getnchannels() != 1
            or source.getsampwidth() != 2
            or source.getframerate() != 16000
        ):
            raise ValueError("Unsupported voice recording format.")
        if source.getnframes() > 16000 * 60:
            raise ValueError("Recording exceeds 60 seconds.")
        data = source.readframes(source.getnframes())
    with sd.RawOutputStream(samplerate=16000, channels=1, dtype="int16") as output:
        output.write(data)
