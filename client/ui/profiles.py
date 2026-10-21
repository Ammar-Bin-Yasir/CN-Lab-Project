"""Profile cards, bounded picture uploads, and reusable circular avatars."""
import base64
from collections import OrderedDict
from pathlib import Path
import weakref
from PySide6.QtCore import Qt, QSize, QByteArray, QBuffer, QIODevice
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QIcon, QImage, QImageReader, QColorSpace
from PySide6.QtWidgets import (QPushButton, QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QFileDialog, QColorDialog, QScrollArea, QWidget)
from shiboken6 import isValid


def text_label(text, name=''):
    label = QLabel(text)
    label.setTextFormat(Qt.PlainText)
    label.setObjectName(name)
    label.setWordWrap(True)
    return label


def avatar_icon(profile, size=40):
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size, size)
    painter.setClipPath(path)
    colors = ['#5865f2', '#337e75', '#9b547c', '#b16e40', '#536e9b']
    painter.fillRect(pix.rect(), QColor(colors[profile.get('id', 0) % len(colors)]))
    image = QImage.fromData(base64.b64decode(profile.get('avatar', '')))
    if not image.isNull():
        painter.drawImage(pix.rect(), image)
    else:
        font = painter.font()
        font.setPixelSize(size // 2)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(Qt.white)
        painter.drawText(pix.rect(), Qt.AlignCenter, profile.get('display_name', '?')[:1].upper())
    painter.end()
    return QIcon(pix)


class Profiles:
    """GUI-thread cache: coalesce avatar requests and bound retained images."""
    def __init__(self, window):
        self.window = window
        self.cache = OrderedDict()
        self.waiting = {}

    def avatar(self, person, size=40):
        item = QPushButton()
        item.setObjectName('avatar')
        item.setFixedSize(size, size)
        item.setIconSize(QSize(size, size))
        item.setToolTip('View ' + person['display_name'] + "'s profile")
        item.setAccessibleName(item.toolTip())
        item.setCursor(Qt.PointingHandCursor)
        item.clicked.connect(lambda: self.window.open_profile(person['id']))
        item.setIcon(avatar_icon(person, size))
        key = (person['id'], person.get('avatar_version', ''))
        if not key[1]:
            return item
        cached = self.cache.get(key)
        if cached:
            item.setIcon(avatar_icon(cached, size))
            return item
        ref = weakref.ref(item)
        def paint(data):
            widget = ref()
            if widget is not None and isValid(widget):
                widget.setIcon(avatar_icon(data, size))
        if key in self.waiting:
            self.waiting[key].append(paint)
            return item
        self.waiting[key] = [paint]
        session = self.window.session
        def loaded(ok, data):
            if session != self.window.session:
                return
            callbacks = self.waiting.pop(key, [])
            if not ok:
                return
            self.cache[key] = data
            while len(self.cache) > 128:
                self.cache.popitem(last=False)
            for callback in callbacks:
                callback(data)
        self.window.adapter.request('profile_get', {'user_id': person['id']}, loaded)
        return item


class ProfileDialog(QDialog):
    def __init__(self, window, profile):
        super().__init__(window)
        self.window, self.profile = window, dict(profile)
        self.own = profile['id'] == window.adapter.profile['id']
        self.setWindowTitle('My profile' if self.own else 'User profile')
        self.setFixedWidth(440)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        layout = QVBoxLayout(content)
        scroll.setWidget(content)
        outer.addWidget(scroll)
        available = window.screen().availableGeometry().height()
        self.resize(440, min(720 if self.own else 550, max(360, available - 100)))
        self.setMaximumHeight(max(360, available - 80))
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        self.banner = QLabel()
        self.banner.setFixedHeight(70)
        layout.addWidget(self.banner)
        self.picture = QPushButton()
        self.picture.setObjectName('avatar')
        self.picture.setFixedSize(80, 80)
        self.picture.setIconSize(QSize(80, 80))
        self.picture.setAccessibleName('Profile picture')
        self.picture.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.picture)
        self.preview()
        layout.addWidget(text_label('@' + profile['username'], 'muted'))
        online = profile['id'] in window.state['online']
        layout.addWidget(text_label('Online' if online else 'Offline', 'muted'))
        self.error = text_label('', 'error')
        if self.own:
            actions = QHBoxLayout()
            for title, action in [('Change picture', self.choose_picture), ('Remove', self.remove_picture), ('Color', self.choose_color)]:
                b = QPushButton(title); b.clicked.connect(action); actions.addWidget(b)
            layout.addLayout(actions)
            layout.addWidget(text_label('Display name'))
            self.name = QLineEdit(profile['display_name']); self.name.setMaxLength(64)
            layout.addWidget(self.name)
            layout.addWidget(text_label('About me · up to 280 characters'))
            self.bio = QTextEdit(); self.bio.setPlainText(profile.get('bio', '')); self.bio.setFixedHeight(100)
            layout.addWidget(self.bio)
            self.save_button = QPushButton('Save changes'); self.save_button.setObjectName('primary')
            self.save_button.clicked.connect(self.save); layout.addWidget(self.save_button)
            layout.addWidget(text_label('Connected to ' + window.adapter.host, 'muted'))
            signout = QPushButton('Sign out'); signout.clicked.connect(self.sign_out); layout.addWidget(signout)
        else:
            layout.addWidget(text_label(profile['display_name'], 'title'))
            layout.addWidget(text_label('ABOUT ME', 'muted'))
            layout.addWidget(text_label(profile.get('bio') or 'No bio yet.'))
            message = QPushButton('Message'); message.setObjectName('primary')
            message.clicked.connect(self.message); layout.addWidget(message)
        layout.addWidget(self.error)
        close = QPushButton('Close'); close.clicked.connect(self.reject); layout.addWidget(close)

    def preview(self):
        self.picture.setIcon(avatar_icon(self.profile, 80))
        self.banner.setStyleSheet('background: ' + self.profile.get('color', '#5865f2') + '; border-radius: 12px;')

    def choose_color(self):
        color = QColorDialog.getColor(QColor(self.profile['color']), self, 'Banner color')
        if color.isValid():
            self.profile['color'] = color.name(); self.preview()

    def remove_picture(self):
        self.profile['avatar'] = ''; self.preview()

    def choose_picture(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Choose profile picture', '', 'Images (*.png *.jpg *.jpeg *.webp)')
        if not path:
            return
        try:
            if Path(path).stat().st_size > 5 * 1024 * 1024:
                raise ValueError('Choose an image smaller than 5 MB.')
            reader = QImageReader(path)
            size = reader.size()
            if not size.isValid() or size.width() > 4096 or size.height() > 4096:
                raise ValueError('Choose an image no larger than 4096 × 4096.')
            reader.setAutoTransform(True)
            image = reader.read()
            if image.isNull():
                raise ValueError('This image could not be opened.')
            side = min(image.width(), image.height())
            image = image.copy((image.width()-side)//2, (image.height()-side)//2, side, side)
            image = image.scaled(96, 96, Qt.IgnoreAspectRatio, Qt.SmoothTransformation).convertToFormat(QImage.Format_RGB888)
            image.setColorSpace(QColorSpace())
            data = QByteArray(); buffer = QBuffer(data); buffer.open(QIODevice.WriteOnly)
            if not image.save(buffer, 'PNG') or len(data) > 32768:
                raise ValueError('Could not prepare this picture.')
            self.profile['avatar'] = base64.b64encode(bytes(data)).decode('ascii')
            self.preview(); self.error.clear()
        except (OSError, ValueError) as error:
            self.error.setText(str(error))

    def save(self):
        if len(self.bio.toPlainText()) > 280:
            self.error.setText('Keep your bio within 280 characters.'); return
        self.save_button.setEnabled(False)
        session = self.window.session
        payload = dict(display_name=self.name.text(), bio=self.bio.toPlainText(), color=self.profile['color'], avatar=self.profile.get('avatar', ''))
        def saved(ok, data):
            if not isValid(self) or session != self.window.session:
                return
            self.save_button.setEnabled(True)
            if not ok:
                self.error.setText(data.get('message', 'Could not save profile.')); return
            self.window.adapter.profile = data
            self.window.refresh()
            self.accept()
        self.window.adapter.request('profile_update', payload, saved)

    def sign_out(self):
        self.reject(); self.window.sign_out()

    def message(self):
        self.accept(); self.window.show_chat(f"user:{self.profile['id']}")
