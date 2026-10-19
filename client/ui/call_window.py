"""Dedicated Qt call controls; background media reports through queued signals."""

from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from client.media.calls import MediaCall


class CallWindow(QDialog):
    media_event = Signal(str, object)
    finished_call = Signal(str)

    def __init__(self, adapter, info, title, parent=None):
        super().__init__(parent)
        self.adapter = adapter
        self.info = info
        self.media = None
        self.ending = False
        self.seconds = 0
        self.setWindowTitle(title)
        self.resize(620, 480 if info["mode"] == "video" else 220)
        layout = QVBoxLayout(self)
        self.status = QLabel("Ringing…")
        layout.addWidget(self.status)
        self.remote = QLabel("Waiting for video")
        self.remote.setAlignment(Qt.AlignCenter)
        self.remote.setMinimumSize(320, 240)
        self.local = QLabel()
        self.local.setFixedSize(160, 120)
        if info["mode"] == "video":
            layout.addWidget(self.remote)
            layout.addWidget(self.local)
        row = QHBoxLayout()
        self.mute_button = QPushButton("Mute microphone")
        self.mute_button.setCheckable(True)
        self.mute_button.toggled.connect(self.mute)
        row.addWidget(self.mute_button)
        end = QPushButton("End call")
        end.clicked.connect(self.close)
        row.addWidget(end)
        layout.addLayout(row)
        self.media_event.connect(self.on_media, Qt.QueuedConnection)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)

    def activate(self):
        if self.media or self.ending:
            return
        self.status.setText("Connecting microphone/media…")
        self.media = MediaCall(
            self.adapter.host,
            self.adapter.media_port,
            self.adapter.token,
            self.info["id"],
            self.info["mode"] == "video",
            lambda k, d: self.media_event.emit(k, d),
        )
        self.media.start()

    def mute(self, value):
        if self.media:
            self.media.mute(value)
        self.mute_button.setText("Unmute microphone" if value else "Mute microphone")

    def tick(self):
        self.seconds += 1
        self.status.setText(
            f"Connected · {self.seconds // 60:02}:{self.seconds % 60:02}"
        )

    def on_media(self, kind, data):
        if self.ending:
            return
        if kind == "active":
            self.status.setText("Media connected")
            self.timer.start(1000)
        elif kind in ("local_video", "remote_video"):
            pixmap = QPixmap()
            if pixmap.loadFromData(data, "JPG"):
                widget = self.local if kind == "local_video" else self.remote
                widget.setPixmap(
                    pixmap.scaled(
                        widget.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
        elif kind == "error":
            self.status.setText("Media failed: " + data)
            self.shutdown()
            self.adapter.request(
                "end_call", {"call_id": self.info["id"]}, lambda *_: None
            )
        elif kind == "ended":
            self.shutdown()

    def shutdown(self, reason="Call ended"):
        if self.ending:
            return
        self.ending = True
        self.timer.stop()
        if self.media:
            self.media.close()
        if not self.status.text().startswith("Media failed"):
            self.status.setText(reason)
        self.finished_call.emit(self.info["id"])

    def closeEvent(self, event):
        if not self.ending:
            self.adapter.request(
                "end_call", {"call_id": self.info["id"]}, lambda *_: None
            )
        self.shutdown()
        event.accept()
