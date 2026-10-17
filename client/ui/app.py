"""Qt presentation layer. All preview data access goes through DemoService."""
import sys
from pathlib import Path
from PySide6.QtCore import Qt, Signal, QStandardPaths, QTimer
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QLineEdit, QTextEdit, QFrame, QScrollArea,
    QDialog, QCheckBox, QMessageBox, QInputDialog, QFileDialog)
from client.demo import DemoService, PEOPLE

# helper to create a QLabel with a style and optional word wrap
def label(text, style='', wrap=False):
    item = QLabel(text)
    item.setTextFormat(Qt.PlainText)
    item.setObjectName(style)
    item.setWordWrap(wrap)
    return item

# helper to create a QPushButton with a style, click action, and optional tooltip
def button(text, action, style='', tip=''):
    item = QPushButton(text)
    item.setObjectName(style)
    item.clicked.connect(action)
    item.setCursor(Qt.PointingHandCursor)
    item.setToolTip(tip or text)
    return item

# helper to clear a layout and delete its widgets and sub-layouts
def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())
            item.layout().deleteLater()

# Additional functionality for the text composer to emit a signal when the user presses Enter without Shift.
class Composer(QTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and not event.modifiers() & Qt.ShiftModifier:
            self.submitted.emit()
        else:
            super().keyPressEvent(event)

# Window is the object that manages what the user sees and how the interface reacts
class Window(QMainWindow):
    def __init__(self, service):
        super().__init__()
        
        # service is the object that manages each clients personal data and requests. 
        self.service = service
        self.target = None
        self.drafts = {}
        
        self.setWindowTitle('Chatters · Desktop preview')
        self.resize(1180, 780)
        self.setMinimumSize(900, 620)
        self.setStyleSheet(Path(__file__).with_name('theme.qss').read_text())

        # builds the fist screen after configs above.
        self.login_screen()

    # builds the login screen
    def login_screen(self):
        root = QWidget()
        outer = QHBoxLayout(root)
        outer.setContentsMargins(60, 40, 60, 40)
        intro = QVBoxLayout()
        intro.addWidget(label('chatters', 'brand'))
        intro.addStretch()
        intro.addWidget(label('A little closer.\nOne conversation at a time.', 'title', True))
        intro.addWidget(label('Your people. Your groups. Your campus.', 'muted'))
        intro.addSpacing(20)
        intro.addWidget(label('DESKTOP PREVIEW\nExplore the interface before we connect the LAN server.\nMessages and profiles stay on this computer.', 'muted', True))
        intro.addStretch()
        outer.addLayout(intro, 1)
        card = QFrame(); card.setObjectName('card'); card.setFixedWidth(370)
        form = QVBoxLayout(card); form.setContentsMargins(28, 32, 28, 32); form.setSpacing(16)
        form.addWidget(label('Welcome back', 'title'))
        form.addWidget(label('Local preview · no server connected', 'muted'))
        self.username = QLineEdit(); self.username.setPlaceholderText('Username'); self.username.setAccessibleName('Username')
        self.display_name = QLineEdit(); self.display_name.setPlaceholderText('Display name (for registration)')
        self.password = QLineEdit(); self.password.setPlaceholderText('Preview password'); self.password.setEchoMode(QLineEdit.Password)
        for field in (self.username, self.display_name, self.password): form.addWidget(field)
        self.auth_error = label('', 'error', True); form.addWidget(self.auth_error)
        form.addWidget(button('Log in to local profile', lambda: self.authenticate(False), 'primary'))
        form.addWidget(button('Create local profile', lambda: self.authenticate(True)))
        form.addWidget(label('Or take a look without creating a profile.', 'muted', True))
        form.addWidget(button('Explore preview  →', self.enter_preview))
        form.addWidget(label('Server discovery and real account login will be connected during the networking phase.', 'muted', True))
        self.password.returnPressed.connect(lambda: self.authenticate(False))
        outer.addWidget(card, 0, Qt.AlignVCenter)
        self.setCentralWidget(root)

    def authenticate(self, register):
        try:
            if register: self.service.register(self.username.text(), self.display_name.text(), self.password.text())
            else: self.service.login(self.username.text(), self.password.text())
        except ValueError as error:
            self.auth_error.setText(str(error)); return
        self.shell()

    def enter_preview(self):
        self.service.preview(); self.shell()

    # Creates the rail, sidebar and main panel
    def shell(self):
        root = QWidget(); row = QHBoxLayout(root); row.setSpacing(0); row.setContentsMargins(0, 0, 0, 0)
        rail = QWidget(); rail.setObjectName('rail'); rail.setFixedWidth(78)
        self.rail = QVBoxLayout(rail); self.rail.setContentsMargins(12, 20, 12, 16); self.rail.setSpacing(12)
        side = QWidget(); side.setObjectName('sidebar'); side.setFixedWidth(242)
        self.side = QVBoxLayout(side); self.side.setContentsMargins(18, 22, 18, 18); self.side.setSpacing(12)
        main = QWidget(); main.setObjectName('main')
        self.main = QVBoxLayout(main); self.main.setContentsMargins(28, 22, 28, 20); self.main.setSpacing(18)
        row.addWidget(rail); row.addWidget(side); row.addWidget(main, 1)
        self.setCentralWidget(root)
        self.show_home()

    def stash_draft(self):
        if self.target and hasattr(self, 'composer'):
            self.drafts[self.target] = self.composer.toPlainText()
        self.target = None

    def navigation(self, group=None):
        clear(self.rail); clear(self.side)
        home = button('C', self.show_home, 'railButton', 'Home · Online people'); home.setFixedSize(52, 52)
        home.setCheckable(True); home.setChecked(group is None); self.rail.addWidget(home)
        for g in self.service.groups(joined=True):
            b = button(g['name'][:2].upper(), lambda checked=False, g=g: self.show_chat('group:' + str(g['id'])), 'railButton', g['name'])
            b.setFixedSize(52, 52); b.setCheckable(True); b.setChecked(group is not None and g['id'] == group['id']); self.rail.addWidget(b)
        self.rail.addWidget(button('+', self.create_group, 'railButton', 'Create group'))
        self.rail.addWidget(button('⌕', self.browse_groups, 'railButton', 'Browse groups'))
        self.rail.addStretch()
        self.rail.addWidget(label('LOCAL', 'muted'))
        if group:
            self.side.addWidget(label(group['name'], 'brand', True))
            self.side.addWidget(label('Password protected' if group['protected'] else 'Public group', 'muted'))
            self.side.addSpacing(20)
            self.side.addWidget(label('MEMBERS', 'muted'))
            self.side.addWidget(label(self.service.name + ' · You', wrap=True))
            self.side.addWidget(label('Live member presence awaits the server.', 'muted', True))
            self.side.addStretch()
            self.side.addWidget(button('Leave group', lambda: self.leave_group(group)))
        else:
            self.side.addWidget(label('chatters', 'brand'))
            self.side.addWidget(label('A space for your people.', 'muted'))
            self.side.addSpacing(16)
            self.side.addWidget(button('Online people', self.show_home, 'nav'))
            self.side.addSpacing(12); self.side.addWidget(label('PRIVATE CONVERSATIONS', 'muted'))
            chats = self.service.conversations()
            for person in chats:
                b = button(PEOPLE[person], lambda checked=False, p=person: self.show_chat(p), 'nav')
                b.setCheckable(True); b.setChecked(self.target == person); self.side.addWidget(b)
            if not chats: self.side.addWidget(label('Choose someone from Home to start a conversation.', 'muted', True))
            self.side.addStretch()
        self.side.addWidget(label(self.service.name, wrap=True))
        self.side.addWidget(label('Preview profile · saved locally', 'muted'))
        self.side.addWidget(button('Sign out', self.sign_out, 'nav'))

    def sign_out(self):
        self.target = None; self.drafts.clear(); self.service.user = None; self.login_screen()

    def preview_banner(self):
        self.main.addWidget(label('LOCAL PREVIEW  /  Sample contacts. Nothing is sent over the network.', 'muted', True))

    # displays the home screen with a list of people to chat with
    def show_home(self):
        self.stash_draft(); self.navigation(); clear(self.main); self.preview_banner()
        self.main.addWidget(label('Your people, right here.', 'title'))
        self.main.addWidget(label('Start a private conversation or bring everyone together in a group.', 'muted', True))
        search = QLineEdit(); search.setPlaceholderText('Find a preview contact…'); self.main.addWidget(search)
        self.main.addWidget(label('SAMPLE PEOPLE — 3', 'muted'))
        for index, (key, name) in enumerate(PEOPLE.items()):
            card = QFrame(); card.setObjectName('card'); line = QHBoxLayout(card); line.setContentsMargins(18, 16, 18, 16)
            avatar = label(name[0], 'brand'); avatar.setFixedWidth(38); line.addWidget(avatar)
            text = QVBoxLayout(); text.addWidget(label(name)); text.addWidget(label('Preview contact · not live presence', 'muted')); line.addLayout(text, 1)
            line.addWidget(button('Message  →', lambda checked=False, p=key: self.show_chat(p)))
            self.main.addWidget(card)
            search.textChanged.connect(lambda value, c=card, n=name: c.setVisible(value.lower() in n.lower()))
        self.main.addStretch()
        self.main.addWidget(label('Make room for a conversation', 'brand'))
        self.main.addWidget(label('No groups yet? Use + on the left to create your first one.\nGroups you join will stay in your navigation rail.', 'muted', True))

    # displays the chat screen for a given target, which can be a person or a group
    def show_chat(self, target):
        self.stash_draft(); self.target = target
        group = next((g for g in self.service.groups(True) if target == f"group:{g['id']}"), None)
        self.navigation(group); clear(self.main); self.preview_banner()
        title = group['name'] if group else PEOPLE[target]
        head = QHBoxLayout(); head.addWidget(label(title, 'title'), 1)
        if not group:
            for name in ('Voice call', 'Video call'):
                b = button(name, lambda: None); b.setEnabled(False); b.setToolTip('Available after live media and networking integration'); head.addWidget(b)
        self.main.addLayout(head)
        self.main.addWidget(label('Group conversation' if group else 'Private conversation · local preview', 'muted'))
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True)
        self.messages = QWidget(); self.message_layout = QVBoxLayout(self.messages); self.message_layout.setContentsMargins(0, 12, 10, 12); self.message_layout.setSpacing(20)
        self.scroll.setWidget(self.messages); self.main.addWidget(self.scroll, 1)
        self.render_messages()
        self.feedback = label('', 'error', True); self.main.addWidget(self.feedback)
        composer_row = QHBoxLayout()
        composer_row.addWidget(button('+', self.preview_attachment, tip='Preview an attachment'))
        self.composer = Composer(); self.composer.setFixedHeight(84); self.composer.setPlaceholderText('Write a message…'); self.composer.setAccessibleName('Message'); self.composer.setPlainText(self.drafts.get(target, ''))
        self.composer.submitted.connect(self.send); composer_row.addWidget(self.composer, 1)
        composer_row.addWidget(button('Send', self.send, 'primary')); self.main.addLayout(composer_row)
        self.main.addWidget(label('Enter to save locally · Shift + Enter for a new line · Voice recording pending media integration', 'muted', True))
        self.composer.setFocus()

    # builds visible message rows.
    def render_messages(self):
        clear(self.message_layout)
        rows = self.service.history(self.target)
        if not rows:
            self.message_layout.addStretch()
            self.message_layout.addWidget(label('This is the start of something.', 'title'))
            self.message_layout.addWidget(label('Say hello. Preview messages are saved only on this computer.', 'muted', True))
        for sender, body, time in rows:
            row = QHBoxLayout(); avatar = label(sender[:1].upper(), 'brand'); avatar.setFixedSize(36, 36); row.addWidget(avatar, 0, Qt.AlignTop)
            column = QVBoxLayout(); column.setSpacing(6)
            header = QHBoxLayout(); header.addWidget(label(sender)); header.addWidget(label(time + ' · Local only', 'muted')); header.addStretch(); column.addLayout(header)
            message = label(body, wrap=True); message.setTextInteractionFlags(Qt.TextSelectableByMouse); column.addWidget(message)
            row.addLayout(column, 1); self.message_layout.addLayout(row)
        self.message_layout.addStretch()
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    # User presses Send or Enter.
    def send(self):
        try: self.service.send(self.target, self.composer.toPlainText())
        except ValueError as error:
            self.feedback.setText(str(error)); return
        self.composer.clear(); self.drafts.pop(self.target, None); self.feedback.clear(); self.render_messages()
        group = next((g for g in self.service.groups(True) if self.target == f"group:{g['id']}"), None)
        self.navigation(group)

    def preview_attachment(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Preview attachment')
        if not path: return
        try:
            size = Path(path).stat().st_size
            if size > 20 * 1024 * 1024: raise ValueError('The attachment limit is 20 MiB.')
            QMessageBox.information(self, 'Attachment preview', f'{Path(path).name}\n{size / 1024:.1f} KiB\n\nFile selection works. Upload and delivery await the networking implementation. No file has been sent or copied.')
        except (OSError, ValueError) as error: self.feedback.setText(str(error))

    # User chooses to create a group
    def create_group(self):
        dialog = QDialog(self); dialog.setWindowTitle('Create a group'); dialog.setMinimumWidth(400)
        layout = QVBoxLayout(dialog); layout.setSpacing(16)
        layout.addWidget(label('Bring your people together.', 'brand'))
        name = QLineEdit(); name.setPlaceholderText('Group name'); layout.addWidget(name)
        protected = QCheckBox('Require a shared password to join'); layout.addWidget(protected)
        password = QLineEdit(); password.setEchoMode(QLineEdit.Password); password.setPlaceholderText('Group password'); password.setEnabled(False); protected.toggled.connect(password.setEnabled); layout.addWidget(password)
        layout.addWidget(label('Members can read saved group history. No admin roles.\nThis creates a local preview group.', 'muted', True))
        error = label('', 'error', True); layout.addWidget(error)
        def create():
            if protected.isChecked() and not password.text(): error.setText('Enter a password or choose a public group.'); return
            try: gid = self.service.create_group(name.text(), password.text() if protected.isChecked() else '')
            except ValueError as exc: error.setText(str(exc)); return
            dialog.accept(); self.show_chat(f'group:{gid}')
        layout.addWidget(button('Create group', create, 'primary')); layout.addWidget(button('Cancel', dialog.reject)); dialog.exec()

    # User wants to find and join groups
    def browse_groups(self):
        dialog = QDialog(self); dialog.setWindowTitle('Browse local groups'); dialog.resize(450, 400)
        layout = QVBoxLayout(dialog); layout.addWidget(label('Find your group', 'title'))
        layout.addWidget(label('Joining gives access to saved group history.', 'muted', True))
        scroll = QScrollArea(); scroll.setWidgetResizable(True); content = QWidget(); groups_layout = QVBoxLayout(content); scroll.setWidget(content); layout.addWidget(scroll)
        groups = self.service.groups()
        if not groups: groups_layout.addWidget(label('No groups yet. Create the first one with +.', 'muted', True))
        for g in groups:
            def join(checked=False, g=g):
                password = ''
                if g['protected'] and not g['joined']:
                    password, ok = QInputDialog.getText(dialog, 'Protected group', 'Shared group password:', QLineEdit.Password)
                    if not ok: return
                try: self.service.join(g['id'], password)
                except ValueError as error: QMessageBox.warning(dialog, 'Cannot join', str(error)); return
                dialog.accept(); self.show_chat(f"group:{g['id']}")
            groups_layout.addWidget(button(g['name'] + (' · Protected' if g['protected'] else ' · Public') + (' · Joined' if g['joined'] else ''), join))
        groups_layout.addStretch(); layout.addWidget(button('Close', dialog.reject)); dialog.exec()

    # User confirms leaving
    def leave_group(self, group):
        result = QMessageBox.question(self, 'Leave group?', 'The group and its messages will remain. You will need to join again to see them.')
        if result == QMessageBox.Yes:
            self.service.leave(group['id']); self.show_home()


def main():
    # QApplication manages the desktop application: mouse clicks, keyboard input,
    # window events, and other Qt behaviour. A Qt Widgets application needs one of these objects.
    app = QApplication(sys.argv)
    app.setApplicationName('ChattersPreview')
    app.setOrganizationName('Chatters')

    # The database is stored in the standard local application data folder for the OS.
    path = Path(
        QStandardPaths.writableLocation(
            QStandardPaths.AppLocalDataLocation
        )
    ) / 'preview.sqlite'

    service = DemoService(path)

    window = Window(service)
    window.show()

    try:
        return app.exec()
    finally:
        service.close()


if __name__ == '__main__':
    sys.exit(main())
