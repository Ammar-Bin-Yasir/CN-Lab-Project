"""Dedicated Qt call controls; background media reports through queued signals."""

from PySide6.QtCore import Signal, QTimer, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QWidget, QSizePolicy
from client.media.calls import MediaCall
from client.ui.dialogs import TaskDialog, text, action
from client.ui.modal import InAppDialog, close_button
from client.ui.profiles import avatar_icon


class CallWindow(InAppDialog):
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
        self.setObjectName('callDialog')
        video = info['mode'] == 'video'
        self.resize(720 if video else 440, 560 if video else 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        top = QHBoxLayout()
        spacer = QWidget()
        spacer.setFixedWidth(32)
        top.addWidget(spacer)
        top.addStretch()
        heading = text(title, 'callName')
        heading.setAlignment(Qt.AlignCenter)
        self.draggable(heading)
        top.addWidget(heading)
        top.addStretch()
        top.addWidget(close_button(self))
        layout.addLayout(top)
        self.status = text('Ringing…', 'dialogDescription')
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status)
        self.remote = QLabel('Waiting for their camera…')
        self.remote.setObjectName('callStage')
        self.remote.setAlignment(Qt.AlignCenter)
        self.remote.setMinimumSize(320, 240)
        self.remote.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.local = QLabel('Your camera')
        self.local.setAlignment(Qt.AlignCenter)
        self.local.setObjectName('localVideo')
        self.local.setFixedSize(144, 108)
        if video:
            stage = QWidget()
            grid = QGridLayout(stage)
            grid.setContentsMargins(0, 0, 0, 0)
            grid.addWidget(self.remote, 0, 0)
            grid.addWidget(self.local, 0, 0, Qt.AlignBottom | Qt.AlignRight)
            layout.addWidget(stage, 1)
        else:
            portrait = QLabel()
            portrait.setAlignment(Qt.AlignCenter)
            portrait.setPixmap(avatar_icon({'display_name': title}, 104).pixmap(104, 104))
            layout.addStretch()
            layout.addWidget(portrait, 0, Qt.AlignCenter)
            layout.addWidget(text('Voice call', 'muted'), 0, Qt.AlignCenter)
            layout.addStretch()
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addStretch()
        self.mute_button = QPushButton('Mute microphone')
        self.mute_button.setObjectName('microphone')
        self.mute_button.setAutoDefault(False)
        self.mute_button.setCheckable(True)
        self.mute_button.setEnabled(False)
        self.mute_button.toggled.connect(self.mute)
        row.addWidget(self.mute_button)
        self.end_button = action('End call', self.close, 'danger')
        row.addWidget(self.end_button)
        row.addStretch()
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
            self.status.setText("Connected · 00:00")
            self.mute_button.setEnabled(True)
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
        self.mute_button.setEnabled(False)
        self.end_button.setText("Close")
        if self.media:
            self.media.close()
        if not self.status.text().startswith("Media failed"):
            self.status.setText(reason)
        self.finished_call.emit(self.info["id"])

    def reject(self):
        self.close()

    def closeEvent(self, event):
        if not self.ending:
            self.adapter.request(
                "end_call", {"call_id": self.info["id"]}, lambda *_: None
            )
        self.shutdown()
        event.accept()


class IncomingCall(TaskDialog):
    def __init__(self, parent, info):
        super().__init__(parent, 'Incoming ' + info['mode'] + ' call',
            info.get('caller_name', 'Someone') + ' is calling.')
        portrait = QLabel()
        portrait.setPixmap(avatar_icon({'display_name': info.get('caller_name', '?')}, 88).pixmap(88, 88))
        self.body.addWidget(portrait, 0, Qt.AlignCenter)
        self.body.addStretch()
        self.footer.addStretch()
        self.footer.addWidget(action('Decline', self.reject, 'danger'))
        self.footer.addWidget(action('Accept call', self.accept, 'primary'))
