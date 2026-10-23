"""Authorized, bounded inline attachment previews for chat messages."""

import re
import tempfile
import uuid
import weakref
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QPoint
from PySide6.QtGui import QBrush, QColor, QImage, QImageReader, QPainter, QPixmap, QPolygon
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QStackedWidget, QVBoxLayout,
)
from shiboken6 import isValid

from client.network import files


IMAGES = {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp'}
VIDEOS = {'.mp4', '.webm', '.mov', '.m4v', '.avi', '.mkv'}
PREVIEW_WIDTH = 420
PREVIEW_HEIGHT = 244
CACHE_LIMIT = 8


def attachment_details(message):
    """Recognize only the server's generated caption; preserve other message text."""
    name = message.get('attachment_name') or 'Attachment'
    caption = message.get('body', '')
    match = re.fullmatch(r'Attachment: (.*) \(([\d,]+) bytes\)', caption)
    generated = bool(match and match.group(1) == name)
    size = int(match.group(2).replace(',', '')) if generated else None
    suffix = Path(name).suffix.lower()
    kind = 'image' if suffix in IMAGES else 'video' if suffix in VIDEOS else 'file'
    return name, size, kind, '' if generated else caption


def size_label(size):
    if size is None:
        return 'Attachment'
    if size < 1024:
        return f'{size} B'
    if size < 1024 * 1024:
        return f'{size / 1024:.1f} KB'
    return f'{size / (1024 * 1024):.1f} MB'


def _preview_image(path):
    reader = QImageReader(str(path))
    dimensions = reader.size()
    if (not dimensions.isValid() or dimensions.width() > 4096
            or dimensions.height() > 4096 or dimensions.width() * dimensions.height() > 16_000_000):
        raise ValueError('This image is too large to preview. Save it to open separately.')
    reader.setScaledSize(dimensions.scaled(840, 488, Qt.KeepAspectRatio))
    image = reader.read()
    if image.isNull():
        raise ValueError('This image could not be previewed. You can still save it.')
    return image


def _video_poster(path):
    """Decode one bounded frame; playback itself stays with Qt Multimedia."""
    import cv2

    try:
        capture = cv2.VideoCapture(str(path))
    except cv2.error:
        return None
    try:
        width = capture.get(cv2.CAP_PROP_FRAME_WIDTH)
        height = capture.get(cv2.CAP_PROP_FRAME_HEIGHT)
        if (width > 4096 or height > 4096 or width * height > 16_000_000):
            return None
        try:
            ok, frame = capture.read()
        except cv2.error:
            return None
        if not ok or frame is None:
            return None
        height, width = frame.shape[:2]
        if not width or not height:
            return None
        scale = min(840 / width, 488 / height, 1)
        if scale < 1:
            frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return QImage(frame.data, frame.shape[1], frame.shape[0], frame.strides[0], QImage.Format_RGB888).copy()
    finally:
        capture.release()


def _poster_pixmap(image):
    canvas = QPixmap(PREVIEW_WIDTH, PREVIEW_HEIGHT)
    canvas.fill(QColor('#15161b'))
    painter = QPainter(canvas)
    painter.setRenderHint(QPainter.Antialiasing)
    if image is not None and not image.isNull():
        picture = QPixmap.fromImage(image).scaled(PREVIEW_WIDTH, PREVIEW_HEIGHT,
            Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap((PREVIEW_WIDTH-picture.width())//2,
            (PREVIEW_HEIGHT-picture.height())//2, picture)
    center = canvas.rect().center()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QBrush(QColor(15, 16, 22, 190)))
    painter.drawEllipse(center, 30, 30)
    painter.setBrush(QBrush(QColor('#f3f3f7')))
    painter.drawPolygon(QPolygon([
        QPoint(center.x()-6, center.y()-11),
        QPoint(center.x()-6, center.y()+11),
        QPoint(center.x()+12, center.y()),
    ]))
    painter.end()
    return canvas


class AttachmentCard(QFrame):
    def __init__(self, window, message):
        super().__init__()
        self.window = window
        self.file_id = message['attachment']
        self.name, self.file_size, self.kind, self.caption = attachment_details(message)
        self.setObjectName('attachmentCard')
        self.setFixedWidth(PREVIEW_WIDTH)
        self.requested = False
        self.path = None
        self.image = None
        self.video_widget = None
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        if self.kind in ('image', 'video'):
            self.stack = QStackedWidget()
            self.stack.setFixedSize(PREVIEW_WIDTH, PREVIEW_HEIGHT)
            self.poster = QLabel('Loading preview…')
            self.poster.setObjectName('attachmentMedia')
            self.poster.setAlignment(Qt.AlignCenter)
            self.poster.setAccessibleName(self.kind.capitalize() + ' preview: ' + self.name)
            self.stack.addWidget(self.poster)
            outer.addWidget(self.stack)
        else:
            self.stack = None
        row = QHBoxLayout()
        row.setContentsMargins(14, 11, 14, 11)
        row.setSpacing(12)
        if self.kind == 'file':
            badge = QLabel((Path(self.name).suffix[1:5] or 'FILE').upper())
            badge.setObjectName('attachmentBadge')
            badge.setAlignment(Qt.AlignCenter)
            badge.setFixedSize(48, 48)
            row.addWidget(badge)
        detail = QVBoxLayout()
        detail.setSpacing(3)
        name = QLabel(self.name)
        name.setObjectName('attachmentName')
        name.setToolTip(self.name)
        name.setTextFormat(Qt.PlainText)
        name.setWordWrap(True)
        detail.addWidget(name)
        self.meta = QLabel(size_label(self.file_size) + (' · Video' if self.kind == 'video' else ' · Image' if self.kind == 'image' else ''))
        self.meta.setObjectName('muted')
        detail.addWidget(self.meta)
        row.addLayout(detail, 1)
        if self.kind == 'video':
            self.play_button = QPushButton('Play')
            self.play_button.setObjectName('attachmentPlay')
            self.play_button.setAccessibleName('Play video ' + self.name)
            self.play_button.setEnabled(False)
            self.play_button.clicked.connect(lambda: self.window.previews.play(self))
            row.addWidget(self.play_button)
        save = QPushButton('Save')
        save.setObjectName('attachmentSave')
        save.setAccessibleName('Save ' + self.name)
        save.clicked.connect(lambda: self.window.save_attachment(self.file_id, self.name))
        row.addWidget(save)
        outer.addLayout(row)

    def loaded(self, image, path=None):
        self.path = path
        self.image = image
        if self.kind == 'video':
            self.poster.setPixmap(_poster_pixmap(image))
        elif image is not None and not image.isNull():
            pixmap = QPixmap.fromImage(image)
            self.poster.setPixmap(pixmap.scaled(PREVIEW_WIDTH, PREVIEW_HEIGHT,
                Qt.KeepAspectRatio, Qt.SmoothTransformation))
        if self.kind == 'video':
            self.play_button.setEnabled(True)

    def failed(self, error):
        self.poster.setText('Preview unavailable')
        self.poster.setToolTip(error)
        self.meta.setText('Preview unavailable · Save to open')
        if self.kind == 'video':
            self.play_button.setEnabled(False)

    def show_video(self):
        if self.video_widget is None:
            self.video_widget = QVideoWidget()
            self.video_widget.setAspectRatioMode(Qt.KeepAspectRatio)
            self.stack.addWidget(self.video_widget)
        self.stack.setCurrentWidget(self.video_widget)
        self.play_button.setText('Pause')

    def stop_video(self):
        if self.stack is not None:
            self.stack.setCurrentWidget(self.poster)
            self.play_button.setText('Play')


class AttachmentPreviews:
    """Two concurrent downloads, eight retained previews, scoped to one login session."""

    def __init__(self, window):
        self.window = window
        self.session = window.session
        self.temp = tempfile.TemporaryDirectory(prefix='chatters-preview-')
        self.cache = OrderedDict()
        self.waiting = {}
        self.queue = []
        self.active_jobs = 0
        self.player = None
        self.active_card = None

    def request(self, card):
        if card.requested or card.kind == 'file':
            return
        card.requested = True
        file_id = card.file_id
        if file_id in self.cache:
            image, path = self.cache[file_id]
            self.cache.move_to_end(file_id)
            card.loaded(image, path)
            return
        if file_id not in self.waiting:
            self.waiting[file_id] = []
            self.queue.append((file_id, card.name, card.kind))
        self.waiting[file_id].append(weakref.ref(card))
        self._pump()

    def _pump(self):
        while self.queue and self.active_jobs < 2:
            file_id, name, kind = self.queue.pop(0)
            self.active_jobs += 1
            suffix = Path(name).suffix.lower()
            path = Path(self.temp.name) / (uuid.uuid4().hex + suffix)
            host, port, token = self.window.adapter.host, self.window.adapter.file_port, self.window.adapter.token
            session = self.session

            def work(p=path, f=file_id, k=kind, h=host, n=port, t=token):
                files.download(h, n, t, f, p)
                if k == 'image':
                    try:
                        return _preview_image(p), None
                    finally:
                        p.unlink(missing_ok=True)
                return _video_poster(p), p

            def done(result, error, f=file_id, p=path, s=session):
                self.active_jobs -= 1
                if s != self.session:
                    p.unlink(missing_ok=True)
                    self._pump()
                    return
                callbacks = self.waiting.pop(f, [])
                if error:
                    p.unlink(missing_ok=True)
                    for ref in callbacks:
                        card = ref()
                        if card is not None and isValid(card):
                            card.failed(error)
                else:
                    image, retained_path = result
                    self.cache[f] = (image, retained_path)
                    for ref in callbacks:
                        card = ref()
                        if card is not None and isValid(card):
                            card.loaded(image, retained_path)
                    self._evict()
                self._pump()

            self.window.background(work, done)

    def _evict(self):
        while len(self.cache) > CACHE_LIMIT:
            for file_id, (_, path) in self.cache.items():
                if self.active_card is None or self.active_card.file_id != file_id:
                    self.cache.pop(file_id)
                    if path:
                        path.unlink(missing_ok=True)
                    break
            else:
                break

    def play(self, card):
        if self.active_card is card and self.player is not None:
            if self.player.playbackState() == QMediaPlayer.PlayingState:
                self.player.pause()
                card.play_button.setText('Play')
            else:
                self.player.play()
                card.play_button.setText('Pause')
            return
        self.stop()
        if not card.path or not card.path.exists():
            card.requested = False
            card.play_button.setEnabled(False)
            card.poster.setText('Loading video…')
            self.request(card)
            return
        if self.player is None:
            self.player = QMediaPlayer(self.window)
            self.audio = QAudioOutput(self.window)
            self.player.setAudioOutput(self.audio)
            self.player.errorOccurred.connect(self._play_error)
            self.player.mediaStatusChanged.connect(self._media_status)
        self.active_card = card
        card.show_video()
        self.player.setVideoOutput(card.video_widget)
        self.player.setSource(QUrl.fromLocalFile(str(card.path)))
        self.player.play()

    def _play_error(self, _error, description):
        if self.active_card is not None and isValid(self.active_card):
            self.active_card.failed(description or 'This video cannot play here.')
            self.stop()

    def _media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.stop()

    def stop(self):
        card = self.active_card
        self.active_card = None
        if self.player is not None:
            self.player.stop()
            self.player.setVideoOutput(None)
            self.player.setSource(QUrl())
        if card is not None and isValid(card):
            card.stop_video()

    def reset(self):
        self.stop()
        self.session = self.window.session
        self.queue.clear()
        self.waiting.clear()
        for _, path in self.cache.values():
            if path:
                path.unlink(missing_ok=True)
        self.cache.clear()
        self.temp.cleanup()
        self.temp = tempfile.TemporaryDirectory(prefix='chatters-preview-')

    def close(self):
        self.stop()
        self.session = -1
        self.queue.clear()
        self.waiting.clear()
        self.temp.cleanup()
