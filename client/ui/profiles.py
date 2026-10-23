"""Profile cards, bounded picture uploads, and reusable circular avatars."""
import base64
from collections import OrderedDict
from pathlib import Path
import weakref
from PySide6.QtCore import Qt, QSize, QByteArray, QBuffer, QIODevice, Signal
from PySide6.QtGui import QPixmap, QPainter, QPainterPath, QColor, QIcon, QImage, QImageReader, QColorSpace
from PySide6.QtWidgets import (QPushButton, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QTextEdit, QFileDialog, QColorDialog, QScrollArea, QWidget, QFrame)
from shiboken6 import isValid
from client.ui.modal import InAppDialog, close_button


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


class ProfileHeader(QWidget):
    resized = Signal()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()


class ProfileDialog(InAppDialog):
    def __init__(self, window, profile):
        super().__init__(window)
        self.window, self.profile = window, dict(profile)
        self.own = profile['id'] == window.adapter.profile['id']
        self.setWindowTitle('My profile' if self.own else 'User profile')
        self.setObjectName('profileDialog')
        self.resize(480, min(720 if self.own else 540, window.screen().availableGeometry().height() - 80))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        self.header = ProfileHeader()
        header_layout = QVBoxLayout(self.header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        self.banner = QLabel(self.header)
        self.banner.setObjectName('profileBanner')
        self.banner.setFixedHeight(120)
        header_layout.addWidget(self.banner)
        self.draggable(self.banner)
        self.dismiss = close_button(self, self.header)
        self.avatar_ring = QFrame(self.header)
        self.avatar_ring.setObjectName('profileAvatarRing')
        self.avatar_ring.setFixedSize(96, 96)
        self.picture = QPushButton()
        self.picture.setObjectName('avatar')
        self.picture.setParent(self.avatar_ring)
        self.picture.setFixedSize(88, 88)
        self.picture.setIconSize(QSize(88, 88))
        self.picture.move(4, 4)
        self.picture.setAccessibleName('Profile picture')
        self.picture.setFocusPolicy(Qt.NoFocus)
        identity = QWidget()
        identity_layout = QVBoxLayout(identity)
        identity_layout.setContentsMargins(28, 52, 28, 18)
        identity_layout.setSpacing(5)
        identity_layout.addWidget(text_label(profile['display_name'], 'profileName'))
        identity_layout.addWidget(text_label('@' + profile['username'], 'muted'))
        online = profile['id'] in window.state['online']
        identity_layout.addWidget(text_label('Online' if online else 'Offline', 'onlineStatus' if online else 'muted'))
        header_layout.addWidget(identity)
        content_layout.addWidget(self.header)
        self.header.resized.connect(self.position_header_controls)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(28, 8, 28, 28)
        layout.setSpacing(12)
        content_layout.addWidget(body)
        self.preview()
        self.error = text_label('', 'error')
        self.error.setVisible(False)
        footer = QFrame()
        footer.setObjectName('dialogFooter')
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.addWidget(self.error)
        actions = QHBoxLayout()
        footer_layout.addLayout(actions)
        outer.addWidget(footer)
        if self.own:
            pictures = QHBoxLayout()
            for title, callback in [('Change picture', self.choose_picture), ('Remove', self.remove_picture), ('Banner color', self.choose_color)]:
                item = QPushButton(title); item.setAutoDefault(False)
                item.clicked.connect(callback); pictures.addWidget(item)
            layout.addLayout(pictures)
            layout.addWidget(text_label('Display name', 'fieldLabel'))
            self.name = QLineEdit(profile['display_name'])
            self.name.setAccessibleName('Display name'); self.name.setMaxLength(64)
            layout.addWidget(self.name)
            layout.addWidget(text_label('About me', 'fieldLabel'))
            self.bio = QTextEdit()
            self.bio.setAcceptRichText(False)
            self.bio.setAccessibleName('About me')
            self.bio.setPlaceholderText('Tell people a little about yourself.')
            self.bio.setPlainText(profile.get('bio', '')); self.bio.setFixedHeight(96)
            layout.addWidget(self.bio)
            self.counter = text_label('', 'muted')
            self.counter.setAlignment(Qt.AlignRight)
            layout.addWidget(self.counter)
            self.bio.textChanged.connect(self.update_counter)
            self.update_counter()
            layout.addWidget(text_label('Connected to ' + window.adapter.host, 'muted'))
            signout = QPushButton('Sign out'); signout.setObjectName('dangerText')
            signout.setAutoDefault(False); signout.clicked.connect(self.sign_out)
            actions.addWidget(signout)
            actions.addStretch()
            cancel = QPushButton('Cancel'); cancel.setAutoDefault(False)
            cancel.clicked.connect(self.reject); actions.addWidget(cancel)
            self.save_button = QPushButton('Save changes'); self.save_button.setObjectName('primary')
            self.save_button.clicked.connect(self.save); actions.addWidget(self.save_button)
        else:
            layout.addWidget(text_label('About me', 'fieldLabel'))
            layout.addWidget(text_label(profile.get('bio') or 'No bio yet.'))
            actions.addStretch()
            close = QPushButton('Close'); close.clicked.connect(self.reject); actions.addWidget(close)
            message = QPushButton('Message'); message.setObjectName('primary')
            message.clicked.connect(self.message); actions.addWidget(message)
        layout.addStretch()

    def update_counter(self):
        count = len(self.bio.toPlainText())
        self.counter.setText(f'{count} / 280')
        self.counter.setAccessibleName(f'About me: {count} of 280 characters')

    def show_error(self, message):
        self.error.setText(message)
        self.error.setVisible(bool(message))

    def preview(self):
        self.picture.setIcon(avatar_icon(self.profile, 88))
        self.banner.setStyleSheet('background: ' + self.profile.get('color', '#5865f2') + ';')

    def position_header_controls(self):
        self.dismiss.move(self.header.width() - 48, 16)
        self.avatar_ring.move(24, 72)
        self.dismiss.raise_()
        self.avatar_ring.raise_()

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
            self.preview(); self.show_error('')
        except (OSError, ValueError) as error:
            self.show_error(str(error))

    def save(self):
        if not self.save_button.isEnabled():
            return
        if not self.name.text().strip():
            self.show_error('Enter a display name.'); self.name.setFocus(); return
        if len(self.bio.toPlainText()) > 280:
            self.show_error('Keep your bio within 280 characters.'); return
        self.save_button.setEnabled(False)
        self.save_button.setText('Saving…')
        self.show_error('')
        session = self.window.session
        payload = dict(display_name=self.name.text(), bio=self.bio.toPlainText(), color=self.profile['color'], avatar=self.profile.get('avatar', ''))
        def saved(ok, data):
            if not isValid(self) or not self.isVisible() or session != self.window.session:
                return
            self.save_button.setEnabled(True)
            self.save_button.setText('Save changes')
            if not ok:
                self.show_error(data.get('message', 'Could not save profile.')); return
            self.window.adapter.profile = data
            self.window.refresh()
            self.accept()
        self.window.adapter.request('profile_update', payload, saved)

    def sign_out(self):
        self.reject(); self.window.sign_out()

    def message(self):
        self.accept(); self.window.show_chat(f"user:{self.profile['id']}")
