"""Consistent task dialogs and asynchronous group flows on the GUI thread."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QCheckBox, QWidget, QScrollArea, QFrame)
from shiboken6 import isValid
from client.ui.modal import InAppDialog, close_button


def text(value, style=''):
    widget = QLabel(value)
    widget.setTextFormat(Qt.PlainText)
    widget.setWordWrap(True)
    widget.setObjectName(style)
    return widget


def action(title, callback, style=''):
    widget = QPushButton(title)
    widget.setObjectName(style)
    widget.setCursor(Qt.PointingHandCursor)
    widget.setAutoDefault(False)
    widget.clicked.connect(callback)
    return widget


class TaskDialog(InAppDialog):
    def __init__(self, parent, title, description, width=480):
        super().__init__(parent)
        self.setObjectName('taskDialog')
        self.setWindowTitle(title)
        self.resize(width, 360)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(28, 24, 28, 24)
        self.body.setSpacing(16)
        heading = QHBoxLayout()
        title_label = text(title, 'title')
        self.draggable(title_label)
        heading.addWidget(title_label, 1)
        heading.addWidget(close_button(self))
        self.body.addLayout(heading)
        self.body.addWidget(text(description, 'dialogDescription'))
        outer.addWidget(body, 1)
        self.error = text('', 'error')
        self.error.hide()
        footer = QFrame()
        footer.setObjectName('dialogFooter')
        footer_layout = QVBoxLayout(footer)
        footer_layout.setContentsMargins(24, 16, 24, 16)
        footer_layout.addWidget(self.error)
        self.footer = QHBoxLayout()
        footer_layout.addLayout(self.footer)
        self.footer.setSpacing(12)
        outer.addWidget(footer)

    def field(self, title, widget):
        label = text(title, 'fieldLabel')
        label.setBuddy(widget)
        self.body.addWidget(label)
        widget.setAccessibleName(title)
        self.body.addWidget(widget)

    def show_error(self, message):
        self.error.setText(message)
        self.error.setVisible(bool(message))


class GroupForm(TaskDialog):
    def __init__(self, window, group=None):
        self.group = group
        super().__init__(window, 'Join group' if group else 'Create a group',
            ('Enter the shared password for ' + group['name'] + '.') if group else
            'Give your people a place to talk. Choose a name and who can join.')
        self.window = window
        self.name = QLineEdit()
        self.name.setMaxLength(40)
        self.name.setPlaceholderText('e.g. Project team')
        self.protected = QCheckBox('Require a shared password')
        if not group:
            self.field('Group name', self.name)
            self.body.addWidget(self.protected)
        self.password = QLineEdit()
        self.password.setMaxLength(128)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText('Shared password')
        self.field('Password', self.password)
        self.password.setEnabled(bool(group))
        self.protected.toggled.connect(self.password.setEnabled)
        self.body.addWidget(text('Members can view saved group history. No admin roles.', 'muted'))
        self.footer.addStretch()
        self.footer.addWidget(action('Cancel', self.reject))
        self.submit_button = action('Join group' if group else 'Create group', self.submit, 'primary')
        self.footer.addWidget(self.submit_button)
        self.name.returnPressed.connect(self.submit)
        self.password.returnPressed.connect(self.submit)
        (self.password if group else self.name).setFocus()

    def submit(self):
        if not self.submit_button.isEnabled():
            return
        if not self.group and not self.name.text().strip():
            self.show_error('Enter a name for your group.'); self.name.setFocus(); return
        if (self.group or self.protected.isChecked()) and not self.password.text():
            self.show_error('Enter the shared password.'); self.password.setFocus(); return
        payload = {'target': f"group:{self.group['id']}", 'password': self.password.text()} if self.group else {
            'name': self.name.text().strip(), 'password': self.password.text() if self.protected.isChecked() else ''}
        self.submit_button.setEnabled(False)
        self.submit_button.setText('Joining…' if self.group else 'Creating…')
        self.show_error('')
        session = self.window.session
        def completed(ok, data):
            # A reply can arrive after Cancel or sign-out; do not reopen navigation.
            if not isValid(self) or not self.isVisible() or session != self.window.session:
                return
            self.submit_button.setEnabled(True)
            self.submit_button.setText('Join group' if self.group else 'Create group')
            if not ok:
                self.show_error(data.get('message', 'Could not complete the request. Try again.')); return
            self.accept()
            self.window.refresh(lambda: self.window.show_chat(data['target']))
        self.window.adapter.request('join_group' if self.group else 'create_group', payload, completed)


class BrowseGroups(TaskDialog):
    def __init__(self, window):
        super().__init__(window, 'Discover groups', 'Find your conversation. Joining gives you access to saved group history.', 560)
        self.window = window
        self.resize(560, 540)
        self.search = QLineEdit()
        self.search.setPlaceholderText('Search groups')
        self.search.setAccessibleName('Search groups')
        self.search.setClearButtonEnabled(True)
        self.body.addWidget(self.search)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        entries = QVBoxLayout(content)
        entries.setContentsMargins(0, 0, 0, 0)
        entries.setSpacing(8)
        scroll.setWidget(content)
        self.body.addWidget(scroll, 1)
        self.rows = []
        for group in window.state['groups']:
            row = QFrame(); row.setObjectName('groupRow')
            layout = QHBoxLayout(row); layout.setContentsMargins(16, 14, 16, 14)
            copy = QVBoxLayout(); copy.setSpacing(6)
            copy.addWidget(text(group['name'], 'fieldLabel'))
            copy.addWidget(text(('Password protected' if group['protected'] else 'Public group') + (' · Joined' if group['joined'] else ''), 'muted'))
            layout.addLayout(copy, 1)
            join = action('Open' if group['joined'] else 'Join', lambda checked=False, g=group: self.join(g))
            join.setAccessibleName(('Open ' if group['joined'] else 'Join ') + group['name'])
            layout.addWidget(join)
            entries.addWidget(row)
            self.rows.append((group['name'].casefold(), row))
        self.empty = text('No groups yet. Create the first one.' if not self.rows else 'No groups match your search.', 'dialogDescription')
        entries.addWidget(self.empty)
        entries.addStretch()
        self.footer.addWidget(action('Create a group', self.create, 'primary'))
        self.footer.addStretch()
        self.footer.addWidget(action('Close', self.reject))
        self.search.textChanged.connect(self.filter)
        self.filter('')

    def filter(self, query):
        found = False
        for name, row in self.rows:
            matches = query.strip().casefold() in name
            row.setVisible(matches)
            found |= matches
        self.empty.setVisible(not found)

    def create(self):
        self.accept()
        GroupForm(self.window).exec()

    def join(self, group):
        if group['joined']:
            self.accept(); self.window.show_chat(f"group:{group['id']}"); return
        if group['protected']:
            form = GroupForm(self.window, group)
            if form.exec() == QDialog.Accepted:
                self.accept()
            return
        # Public joins use the same pending/error handling, without a password prompt.
        self.show_error('')
        self.search.setPlaceholderText('Joining group…')
        self.search.setEnabled(False)
        for _, row in self.rows:
            row.setEnabled(False)
        session = self.window.session
        def completed(ok, data):
            if not isValid(self) or not self.isVisible() or session != self.window.session:
                return
            self.search.setEnabled(True)
            self.search.setPlaceholderText('Search groups')
            for _, row in self.rows:
                row.setEnabled(True)
            if not ok:
                self.show_error(data.get('message', 'Could not join. Try again.')); return
            self.accept()
            self.window.refresh(lambda: self.window.show_chat(data['target']))
        self.window.adapter.request('join_group', {'target': f"group:{group['id']}", 'password': ''}, completed)
