"""Raw 16 kHz mono signed 16-bit audio, 20 ms blocks."""

from queue import Queue, Empty, Full


class AudioDevice:
    def __init__(self, outgoing):
        self.outgoing = outgoing
        self.playback = Queue(maxsize=8)
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
            try:
                data = self.playback.get_nowait()
            except Empty:
                data = b"\0" * len(outdata)
            outdata[:] = data if len(data) == len(outdata) else b"\0" * len(outdata)

        self.stream = sd.RawStream(
            samplerate=16000,
            blocksize=320,
            channels=1,
            dtype="int16",
            callback=callback,
        )
        self.stream.start()

    def receive(self, block):
        if len(block) != 640:
            return
        try:
            self.playback.put_nowait(block)
        except Full:
            pass

    def close(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
