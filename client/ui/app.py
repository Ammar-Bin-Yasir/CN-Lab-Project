"""Chatters real desktop client. UI operations are asynchronous network requests."""

import sys
import tempfile, uuid, wave
from pathlib import Path
from datetime import datetime
from threading import Thread
from client.network import files
from client.media.recording import Recorder, play
from client.ui.call_window import CallWindow
from PySide6.QtCore import Qt, Signal, QTimer, QObject
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QTextEdit,
    QFrame,
    QScrollArea,
    QDialog,
    QCheckBox,
    QMessageBox,
    QInputDialog,
    QFileDialog,
)
from client.network.adapter import NetworkAdapter
from client.network.discovery import discover


def label(text, style="", wrap=False):
    item = QLabel(str(text))
    item.setTextFormat(Qt.PlainText)
    item.setObjectName(style)
    item.setWordWrap(wrap)
    return item


def button(text, action, style="", tip=""):
    item = QPushButton(text)
    item.setObjectName(style)
    item.clicked.connect(action)
    item.setToolTip(tip or text)
    item.setCursor(Qt.PointingHandCursor)
    return item


def clear(layout):
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            item.widget().hide()
            item.widget().deleteLater()
        elif item.layout():
            clear(item.layout())
            item.layout().deleteLater()


class Composer(QTextEdit):
    submitted = Signal()

    def keyPressEvent(self, event):
        if (
            event.key() in (Qt.Key_Return, Qt.Key_Enter)
            and not event.modifiers() & Qt.ShiftModifier
        ):
            self.submitted.emit()
        else:
            super().keyPressEvent(event)


class DiscoveryBridge(QObject):
    found = Signal(object)
    work_done = Signal(object, object, object)
    progress = Signal(str)
    voice_status = Signal(str, str)


class Window(QMainWindow):
    def __init__(self, adapter):
        super().__init__()
        self.adapter = adapter
        self.target = None
        self.drafts = {}
        self.histories = {}
        self.unread = {}
        self.state = dict(people=[], groups=[], conversations=[], online=[])
        self.include_offline = False
        self.session = 0
        self.history_serial = 0
        self.pending_sends = set()
        self.setWindowTitle("Chatters")
        self.resize(1180, 780)
        self.setMinimumSize(900, 620)
        self.setStyleSheet(Path(__file__).with_name("theme.qss").read_text())
        adapter.connected.connect(self.connected)
        adapter.disconnected.connect(self.lost)
        adapter.server_event.connect(self.on_server_event)
        self.discovery = DiscoveryBridge()
        self.discovery.found.connect(self.discovered)
        self.discovery.work_done.connect(self.work_done)
        self.discovery.progress.connect(self.transfer_progress)
        self.call_states = {}
        self.call_window = None
        self.record_dialog = None
        self.transferring = False
        self.recording_busy = False
        self.transfer_error = ""
        self.active_voice = None
        self.voice_cards = {}
        self.voice_statuses = {}
        self.discovery.voice_status.connect(self.update_voice_status)
        self.login_screen()

    def background(self, task, done):
        def run():
            try:
                result = task()
                error = None
            except Exception as exc:
                result = None
                error = str(exc)
            self.discovery.work_done.emit(done, result, error)

        Thread(target=run, name="chatters-task", daemon=True).start()

    def work_done(self, done, result, error):
        done(result, error)

    def transfer_progress(self, text):
        if self.target and hasattr(self, "feedback"):
            self.feedback.setText(text)

    def login_screen(self):
        self.voice_cards.clear()
        self.session += 1
        self.target = None
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(60, 40, 60, 40)
        intro = QVBoxLayout()
        intro.addWidget(label("chatters", "brand"))
        intro.addStretch()
        intro.addWidget(
            label("A little closer.\nOne conversation at a time.", "title", True)
        )
        intro.addWidget(label("Your people. Your groups. Your LAN.", "muted"))
        intro.addStretch()
        row.addLayout(intro, 1)
        card = QFrame()
        card.setObjectName("card")
        card.setFixedWidth(390)
        form = QVBoxLayout(card)
        form.setContentsMargins(28, 28, 28, 28)
        form.setSpacing(14)
        form.addWidget(label("Welcome to Chatters", "title", True))
        form.addWidget(
            label("Connect to the computer running the server.", "muted", True)
        )
        self.address = QLineEdit("127.0.0.1:5050")
        self.address.setAccessibleName("Server address")
        form.addWidget(self.address)
        form.addWidget(button("Find LAN server", self.find_servers))
        self.connect_button = button("Connect", self.connect_server, "primary")
        form.addWidget(self.connect_button)
        self.connection_status = label("Not connected", "muted", True)
        form.addWidget(self.connection_status)
        self.username = QLineEdit()
        self.username.setPlaceholderText("Username")
        self.display_name = QLineEdit()
        self.display_name.setPlaceholderText("Display name (for new accounts)")
        self.password = QLineEdit()
        self.password.setPlaceholderText("Password · 8–128 characters")
        self.password.setEchoMode(QLineEdit.Password)
        for field in (self.username, self.display_name, self.password):
            form.addWidget(field)
        self.auth_error = label("", "error", True)
        form.addWidget(self.auth_error)
        self.login_button = button(
            "Log in", lambda: self.authenticate(False), "primary"
        )
        self.register_button = button("Create account", lambda: self.authenticate(True))
        form.addWidget(self.login_button)
        form.addWidget(self.register_button)
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
        self.password.returnPressed.connect(lambda: self.authenticate(False))
        row.addWidget(card, 0, Qt.AlignVCenter)
        self.setCentralWidget(root)

    def find_servers(self):
        self.connection_status.setText("Finding servers…")
        Thread(
            target=lambda: self.discovery.found.emit(discover()), daemon=True
        ).start()

    def discovered(self, servers):
        if self.adapter.profile:
            return
        if not servers:
            self.connection_status.setText(
                "No server found. Enter its LAN address manually."
            )
            return
        choices = [f"{s['name']} · {s['host']}:{s['port']}" for s in servers]
        selected, ok = QInputDialog.getItem(
            self, "LAN servers", "Choose server", choices, 0, False
        )
        if ok:
            server = servers[choices.index(selected)]
            self.address.setText(f"{server['host']}:{server['port']}")
            self.connect_server()

    def connect_server(self):
        try:
            host, port = self.address.text().strip().rsplit(":", 1)
            port = int(port)
            if not host or not 1 <= port <= 65535:
                raise ValueError()
        except ValueError:
            self.connection_status.setText("Use an address such as 192.168.1.10:5050.")
            return
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
        self.connection_status.setText("Connecting…")
        self.adapter.connect_server(host, port)

    def connected(self):
        self.connection_status.setText("Connected · sign in to continue")
        self.login_button.setEnabled(True)
        self.register_button.setEnabled(True)

    def lost(self, reason):
        if self.call_window:
            self.call_window.shutdown("Connection lost")
        if self.record_dialog:
            self.record_dialog.reject()
        if self.target:
            self.stash_draft()
        if hasattr(self, "side") and self.adapter.profile is None:
            self.login_screen()
        self.connection_status.setText("Disconnected. Connect again to sign in.")
        self.auth_error.setText(reason)
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)

    def authenticate(self, register):
        if not self.login_button.isEnabled():
            return
        auth_session = self.session
        self.auth_error.setText("Signing in…" if not register else "Creating account…")
        self.login_button.setEnabled(False)
        self.register_button.setEnabled(False)
        payload = dict(username=self.username.text(), password=self.password.text())
        if register:
            payload["display_name"] = self.display_name.text()

        def result(ok, data):
            if auth_session != self.session:
                return
            if not ok:
                self.auth_error.setText(data["message"])
                self.login_button.setEnabled(self.adapter.ready)
                self.register_button.setEnabled(self.adapter.ready)
                return
            self.adapter.profile = data["profile"]
            self.adapter.token = data["token"]
            self.adapter.file_port = data["file_port"]
            self.adapter.media_port = data["media_port"]
            self.password.clear()
            self.shell()
            self.refresh()

        self.adapter.request("register" if register else "login", payload, result)

    def shell(self):
        root = QWidget()
        row = QHBoxLayout(root)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        rail = QWidget()
        rail.setObjectName("rail")
        rail.setFixedWidth(78)
        self.rail = QVBoxLayout(rail)
        self.rail.setContentsMargins(12, 20, 12, 16)
        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(242)
        self.side = QVBoxLayout(side)
        self.side.setContentsMargins(18, 22, 18, 18)
        main = QWidget()
        main.setObjectName("main")
        self.main = QVBoxLayout(main)
        self.main.setContentsMargins(28, 22, 28, 20)
        self.main.setSpacing(16)
        row.addWidget(rail)
        row.addWidget(side)
        row.addWidget(main, 1)
        self.setCentralWidget(root)
        self.show_home()

    def request(self, kind, payload, on_success=None):
        session = self.session

        def result(ok, data):
            if session != self.session:
                return
            if ok:
                if on_success:
                    on_success(data)
            else:
                QMessageBox.warning(
                    self, "Request failed", data.get("message", "Unknown error")
                )

        self.adapter.request(kind, payload, result)

    def refresh(self, on_complete=None):
        session = self.session

        def result(ok, data):
            if not ok or session != self.session or not self.adapter.profile:
                return
            self.state = data
            if self.target:
                if self.target.startswith("group:") and not self.group(self.target):
                    self.show_home()
                else:
                    self.navigation()
            else:
                self.show_home()

            if on_complete:
                on_complete()

        self.adapter.request("snapshot", {}, result)

    def on_server_event(self, kind, data):
        if not self.adapter.profile:
            return
        if kind == "call_incoming":
            if self.call_window and not self.call_window.ending or self.recording_busy:
                self.adapter.request(
                    "reject_call", {"call_id": data["id"]}, lambda *_: None
                )
                return
            accepted = (
                QMessageBox.question(
                    self,
                    "Incoming " + data["mode"] + " call",
                    data.get("caller_name", "Someone") + " is calling. Accept?",
                )
                == QMessageBox.Yes
            )
            if accepted:
                self.make_call_window(data, data.get("caller_name", "Incoming call"))
                self.request(
                    "accept_call",
                    {"call_id": data["id"]},
                    lambda result: self.call_window.activate(),
                )
            else:
                self.adapter.request(
                    "reject_call", {"call_id": data["id"]}, lambda *_: None
                )
        elif kind == "call_state":
            self.call_states[data["id"]] = data
            if self.call_window and self.call_window.info["id"] == data["id"]:
                if data["state"] == "active":
                    self.call_window.activate()
                elif data["state"] == "ended":
                    self.call_window.shutdown(data.get("reason", "Call ended"))
        elif kind == "refresh":
            self.refresh()
        elif kind == "message_received":
            target = data["target"]
            if target == self.target:
                self.load_history()
            else:
                self.unread[target] = self.unread.get(target, 0) + 1
                self.navigation()

    def group(self, target):
        return next(
            (
                g
                for g in self.state["groups"]
                if f"group:{g['id']}" == target and g["joined"]
            ),
            None,
        )

    def person(self, target):
        return next(
            (p for p in self.state["people"] if f"user:{p['id']}" == target), None
        )

    def stash_draft(self):
        if self.target and hasattr(self, "composer"):
            self.drafts[self.target] = self.composer.toPlainText()

    def navigation(self):
        clear(self.rail)
        clear(self.side)
        self.rail.addWidget(button("C", self.show_home, "railButton", "Home"))
        for group in self.state["groups"]:
            if group["joined"]:
                target = f"group:{group['id']}"
                count = self.unread.get(target, 0)
                self.rail.addWidget(
                    button(
                        group["name"][:2].upper() + (" •" if count else ""),
                        lambda checked=False, t=target: self.show_chat(t),
                        "railButton",
                        group["name"],
                    )
                )
        self.rail.addWidget(
            button("+", self.create_group, "railButton", "Create group")
        )
        self.rail.addWidget(
            button("⌕", self.browse_groups, "railButton", "Browse groups")
        )
        self.rail.addStretch()
        self.rail.addWidget(label("LAN", "muted"))
        group = self.group(self.target)
        if group:
            self.side.addWidget(label(group["name"], "brand", True))
            self.side.addWidget(
                label(
                    "Protected group" if group["protected"] else "Public group", "muted"
                )
            )
            self.side.addWidget(label("MEMBERS", "muted"))
            self.member_box = QVBoxLayout()
            self.side.addLayout(self.member_box)
            current = self.target
            session = self.session

            def members(data):
                if self.target != current or self.session != session:
                    return
                clear(self.member_box)
                for p in data:
                    self.member_box.addWidget(
                        label(
                            p["display_name"]
                            + (
                                " · Online"
                                if p["id"] in self.state["online"]
                                else " · Offline"
                            ),
                            "muted",
                            True,
                        )
                    )

            self.request("members", {"target": current}, members)
            self.side.addStretch()
            self.side.addWidget(button("Leave group", self.leave_group))
        else:
            self.side.addWidget(label("chatters", "brand"))
            self.side.addWidget(button("Online people", self.show_home, "nav"))
            self.side.addWidget(label("PRIVATE CONVERSATIONS", "muted"))
            for target in self.state["conversations"]:
                person = self.person(target)
                if person:
                    count = self.unread.get(target, 0)
                    self.side.addWidget(
                        button(
                            person["display_name"] + (f" ({count})" if count else ""),
                            lambda checked=False, t=target: self.show_chat(t),
                            "nav",
                        )
                    )
            self.side.addStretch()
        self.side.addWidget(label(self.adapter.profile["display_name"], wrap=True))
        self.side.addWidget(label("Connected to " + self.adapter.host, "muted", True))
        self.side.addWidget(button("Sign out", self.sign_out, "nav"))
        if self.target and hasattr(self, "send_button"):
            person = self.person(self.target)
            enabled = bool(group or person)
            self.send_button.setEnabled(
                enabled and self.target not in self.pending_sends
            )
            self.composer.setEnabled(enabled)

    def show_home(self):
        self.voice_cards.clear()
        self.stash_draft()
        self.target = None
        self.navigation()
        clear(self.main)
        self.main.addWidget(label("Your people, right here.", "title"))
        self.main.addWidget(label("People connected to this Chatters server", "muted"))
        search = QLineEdit()
        search.setPlaceholderText("Find someone…")
        self.main.addWidget(search)
        include_offline = QCheckBox("Include offline people")
        include_offline.setChecked(self.include_offline)
        self.main.addWidget(include_offline)
        people = sorted(
            self.state["people"],
            key=lambda p: (p["id"] not in self.state["online"], p["display_name"].lower()),
        )
        cards = []
        empty = label(
            "No other accounts yet. Ask a teammate to register." if not people else
            "No matching people. Try another search or include offline people.",
            "muted", True,
        )
        self.main.addWidget(empty)
        for person in people:
            card = QFrame()
            card.setObjectName("card")
            row = QHBoxLayout(card)
            row.addWidget(label(person["display_name"], "brand"), 1)
            online = person["id"] in self.state["online"]
            row.addWidget(label(
                "@" + person["username"] + (" · Online" if online else " · Offline"),
                "muted",
            ))
            row.addWidget(
                button(
                    "Message →",
                    lambda checked=False, p=person: self.show_chat(f"user:{p['id']}"),
                )
            )
            self.main.addWidget(card)
            cards.append((card, person))

        def filter_people():
            self.include_offline = include_offline.isChecked()
            text = search.text().lower()
            any_visible = False
            for card, person in cards:
                matches = text in (person["display_name"] + person["username"]).lower()
                visible = self.include_offline or person["id"] in self.state["online"]
                card.setVisible(matches and visible)
                any_visible = any_visible or matches and visible
            empty.setVisible(not any_visible)

        search.textChanged.connect(filter_people)
        include_offline.toggled.connect(filter_people)
        filter_people()
        self.main.addStretch()
        self.main.addWidget(
            label("Use + to create a group, or ⌕ to browse groups.", "muted", True)
        )

    def show_chat(self, target):
        self.voice_cards.clear()
        self.stash_draft()
        self.target = target
        self.unread.pop(target, None)
        group = self.group(target)
        person = self.person(target)
        if not group and not person:
            self.show_home()
            return
        clear(self.main)
        head = QHBoxLayout()
        head.addWidget(
            label(group["name"] if group else person["display_name"], "title"), 1
        )
        if person:
            for text, mode in (("Voice call", "voice"), ("Video call", "video")):
                b = button(text, lambda checked=False, m=mode: self.start_call(m))
                b.setEnabled(person["id"] in self.state["online"])
                head.addWidget(b)
        self.main.addLayout(head)
        self.main.addWidget(
            label(
                "Group history" if group else
                "Private conversation · Server stores text while the recipient is offline",
                "muted", True,
            )
        )
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        widget = QWidget()
        self.message_layout = QVBoxLayout(widget)
        self.scroll.setWidget(widget)
        self.main.addWidget(self.scroll, 1)
        self.feedback = label("Loading history…", "muted", True)
        self.main.addWidget(self.feedback)
        row = QHBoxLayout()
        self.attach_button = button("+", self.attach_file, tip="Attach file")
        row.addWidget(self.attach_button)
        row.addWidget(
            button(
                "Record",
                self.record_voice,
                tip="Record a voice message, up to 60 seconds",
            )
        )
        self.composer = Composer()
        self.composer.setFixedHeight(84)
        self.composer.setPlaceholderText("Write a message…")
        self.composer.setPlainText(self.drafts.get(target, ""))
        self.composer.submitted.connect(self.send)
        row.addWidget(self.composer, 1)
        self.send_button = button("Send", self.send, "primary")
        row.addWidget(self.send_button)
        self.main.addLayout(row)
        self.main.addWidget(
            label("Enter to send · Shift + Enter for a new line", "muted")
        )
        self.navigation()
        self.load_history()
        self.composer.setFocus()

    def load_history(self):
        target = self.target
        if not target:
            return
        self.history_serial += 1
        serial = self.history_serial
        session = self.session

        def result(ok, data):
            if (
                self.target != target
                or self.session != session
                or serial != self.history_serial
            ):
                return
            if ok:
                self.histories[target] = data
                self.feedback.setText("")
                self.render_messages(data)
            else:
                self.feedback.setText(data["message"])

        self.adapter.request("history", {"target": target}, result)

    def render_messages(self, rows):
        bar = self.scroll.verticalScrollBar()
        stick = bar.maximum() - bar.value() < 30
        old = bar.value()
        clear(self.message_layout)
        self.voice_cards.clear()
        if not rows:
            self.message_layout.addWidget(
                label("This is the start of your conversation.", "muted", True)
            )
        for message in rows:
            layout = QHBoxLayout()
            layout.addWidget(
                label(message["sender"][:1].upper(), "brand"), 0, Qt.AlignTop
            )
            body = QVBoxLayout()
            try:
                stamp = (
                    datetime.fromisoformat(message["created"])
                    .astimezone()
                    .strftime("%b %d · %H:%M")
                )
            except ValueError:
                stamp = message["created"]
            body.addWidget(label(message["sender"] + "  ·  " + stamp, "muted"))
            name = message.get("attachment_name") or "attachment"
            voice = bool(message.get("attachment")) and name.startswith("chatters-voice-") and name.endswith(".wav")
            if voice:
                body.addWidget(self.voice_message_card(message["attachment"]), 0, Qt.AlignLeft)
            else:
                text = label(message["body"], wrap=True)
                text.setTextInteractionFlags(Qt.TextSelectableByMouse)
                body.addWidget(text)
                if message.get("attachment"):
                    body.addWidget(
                        button(
                            "Save " + (name if len(name) <= 45 else name[:42] + "…") + "…",
                            lambda checked=False, f=message["attachment"], n=name: self.save_attachment(f, n),
                        )
                    )
            layout.addLayout(body, 1)
            self.message_layout.addLayout(layout)
        self.message_layout.addStretch()
        QTimer.singleShot(
            0, self.scroll, lambda: bar.setValue(bar.maximum() if stick else old)
        )

    def voice_message_card(self, file_id):
        card = QFrame()
        card.setObjectName("voiceMessage")
        card.setFixedWidth(360)
        row = QHBoxLayout(card)
        row.setContentsMargins(12, 10, 12, 10)
        row.setSpacing(12)
        play_button = button("▶", lambda: self.play_voice(file_id), "voicePlay", "Play voice message")
        play_button.setAccessibleName("Play voice message")
        play_button.setFixedSize(40, 40)
        play_button.setEnabled(self.active_voice is None)
        row.addWidget(play_button)
        details = QVBoxLayout()
        details.setSpacing(3)
        details.addWidget(label("Voice message", "voiceTitle"))
        status = label(self.voice_statuses.get(file_id, "Audio recording"), "muted")
        details.addWidget(status)
        row.addLayout(details, 1)
        save = button("↓", lambda: self.save_attachment(file_id, "voice-message.wav"), "voiceSave", "Save voice message")
        save.setAccessibleName("Save voice message")
        save.setFixedSize(32, 32)
        row.addWidget(save)
        self.voice_cards[file_id] = (play_button, status)
        return card

    def update_voice_status(self, file_id, text):
        self.voice_statuses[file_id] = text
        for current, (play_button, status) in self.voice_cards.items():
            play_button.setEnabled(self.active_voice is None)
            if current == file_id:
                status.setText(text)

    def send(self):
        target = self.target
        text = self.composer.toPlainText()
        if not text.strip() or not self.send_button.isEnabled():
            return
        self.pending_sends.add(target)
        self.send_button.setEnabled(False)
        self.feedback.setText("Sending…")
        session = self.session

        def result(ok, data):
            self.pending_sends.discard(target)
            if session != self.session:
                return
            if self.target == target:
                if ok:
                    if self.composer.toPlainText() == text:
                        self.composer.clear()
                    self.feedback.setText("Accepted by server")
                    self.load_history()
                else:
                    self.feedback.setText(data["message"])
                self.navigation()
            elif ok and self.drafts.get(target) == text:
                self.drafts.pop(target, None)
            self.refresh()

        self.adapter.request("send_message", dict(target=target, body=text), result)

    def create_group(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Create group")
        layout = QVBoxLayout(dialog)
        name = QLineEdit()
        name.setPlaceholderText("Group name")
        layout.addWidget(name)
        protected = QCheckBox("Require a shared password")
        layout.addWidget(protected)
        password = QLineEdit()
        password.setEchoMode(QLineEdit.Password)
        password.setEnabled(False)
        protected.toggled.connect(password.setEnabled)
        layout.addWidget(password)
        layout.addWidget(
            label(
                "Members can view saved group history. No admin roles.", "muted", True
            )
        )
        error = label("", "error", True)
        layout.addWidget(error)

        def submit():
            if protected.isChecked() and not password.text():
                error.setText("Enter a shared password.")
                return
            self.request(
                "create_group",
                dict(
                    name=name.text(),
                    password=password.text() if protected.isChecked() else "",
                ),
                lambda data: (
                    dialog.accept(),
                    self.refresh(lambda: self.show_chat(data["target"])),
                ),
            )

        layout.addWidget(button("Create", submit, "primary"))
        layout.addWidget(button("Cancel", dialog.reject))
        dialog.exec()

    def browse_groups(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Browse groups")
        dialog.resize(420, 360)
        layout = QVBoxLayout(dialog)
        layout.addWidget(
            label("Joining grants access to saved group history.", "muted", True)
        )
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        entries = QVBoxLayout(content)
        scroll.setWidget(content)
        layout.addWidget(scroll)
        for group in self.state["groups"]:

            def join(checked=False, g=group):
                target = f"group:{g['id']}"
                if g["joined"]:
                    dialog.accept()
                    self.show_chat(target)
                    return
                password = ""
                if g["protected"]:
                    password, ok = QInputDialog.getText(
                        dialog,
                        "Protected group",
                        "Shared password:",
                        QLineEdit.Password,
                    )
                    if not ok:
                        return
                self.request(
                    "join_group",
                    dict(target=target, password=password),
                    lambda data: (
                        dialog.accept(),
                        self.refresh(lambda: self.show_chat(data["target"])),
                    ),
                )

            entries.addWidget(
                button(
                    group["name"]
                    + (" · Protected" if group["protected"] else " · Public")
                    + (" · Joined" if group["joined"] else ""),
                    join,
                )
            )
        if not self.state["groups"]:
            entries.addWidget(label("No groups yet. Create the first one.", "muted"))
        entries.addStretch()
        layout.addWidget(button("Close", dialog.reject))
        dialog.exec()

    def leave_group(self):
        if (
            QMessageBox.question(
                self,
                "Leave group?",
                "The group and saved messages will remain. Rejoining may require its password.",
            )
            == QMessageBox.Yes
        ):
            self.request(
                "leave_group",
                dict(target=self.target),
                lambda data: (self.show_home(), self.refresh()),
            )

    def attach_file(self):
        if self.transferring:
            return
        path, _ = QFileDialog.getOpenFileName(self, "Send attachment")
        if path:
            self.upload_file(path)

    def upload_file(self, path, temporary=False):
        if self.transferring:
            return
        target = self.target
        if not target:
            return
        self.transferring = True
        session = self.session
        host, port, token = (
            self.adapter.host,
            self.adapter.file_port,
            self.adapter.token,
        )

        def done(result, error):
            self.transferring = False
            if temporary:
                Path(path).unlink(missing_ok=True)
            if session != self.session:
                return
            if error:
                QMessageBox.warning(self, "Transfer failed", error)
            elif self.target == target:
                self.load_history()
            self.refresh()

        self.background(
            lambda: files.upload(
                host,
                port,
                token,
                target,
                path,
                lambda n, total: self.discovery.progress.emit(
                    f"Uploading… {n * 100 // max(total, 1)}%"
                ),
            ),
            done,
        )

    def save_attachment(self, file_id, name="attachment"):
        if self.transferring:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save attachment (choose a filename)", name
        )
        if not path:
            return
        self.transferring = True
        session = self.session
        host, port, token = (
            self.adapter.host,
            self.adapter.file_port,
            self.adapter.token,
        )

        def done(result, error):
            self.transferring = False
            if session != self.session:
                return
            if error:
                QMessageBox.warning(self, "Download failed", error)
            else:
                self.transfer_progress("Saved and checksum verified: " + str(result))
                if (
                    Path(path).suffix.lower() == ".wav"
                    and QMessageBox.question(
                        self, "Voice recording", "Play the saved WAV recording?"
                    )
                    == QMessageBox.Yes
                ):
                    self.background(
                        lambda: play(path),
                        lambda result, error: QMessageBox.warning(
                            self, "Playback failed", error
                        )
                        if error
                        else None,
                    )

        self.background(
            lambda: files.download(
                host,
                port,
                token,
                file_id,
                path,
                lambda n, total: self.discovery.progress.emit(
                    f"Downloading… {n * 100 // max(total, 1)}%"
                ),
            ),
            done,
        )

    def play_voice(self, file_id):
        if self.active_voice or self.call_window and not self.call_window.ending or self.recording_busy:
            return
        host, port, token = (
            self.adapter.host,
            self.adapter.file_port,
            self.adapter.token,
        )
        path = Path(tempfile.gettempdir()) / (
            "chatters-play-" + uuid.uuid4().hex + ".wav"
        )

        session = self.session
        self.active_voice = file_id
        self.update_voice_status(file_id, "Loading audio…")

        def task():
            try:
                files.download(host, port, token, file_id, path)
                with wave.open(str(path), "rb") as source:
                    seconds = round(source.getnframes() / source.getframerate())
                duration = f"{seconds // 60}:{seconds % 60:02}"
                self.discovery.voice_status.emit(file_id, "Playing · " + duration)
                play(path)
                return duration
            finally:
                path.unlink(missing_ok=True)

        def finished(duration, error):
            self.active_voice = None
            if session != self.session:
                return
            self.update_voice_status(file_id, "Could not play · Try again" if error else duration + " · Audio recording")
            if error:
                QMessageBox.warning(self, "Playback failed", error)

        self.background(task, finished)

    def record_voice(self):
        if self.recording_busy or self.transferring:
            return
        if self.call_window and not self.call_window.ending:
            QMessageBox.information(
                self, "Microphone busy", "End the live call before recording."
            )
            return
        self.recording_busy = True
        recorder = Recorder()
        session = self.session
        target = self.target

        def ready(result, error):
            if session != self.session:
                self.background(lambda: recorder.finish(), lambda *_: None)
                self.recording_busy = False
                return
            if error:
                self.recording_busy = False
                QMessageBox.warning(self, "Microphone unavailable", error)
                return
            dialog = QDialog(self)
            self.record_dialog = dialog
            dialog.setWindowTitle("Record voice message")
            layout = QVBoxLayout(dialog)
            timer_label = label("Recording… 0 / 60 seconds")
            layout.addWidget(timer_label)
            timer = QTimer(dialog)
            elapsed = [0]
            finished = [False]

            def finish(send=False):
                if finished[0]:
                    return
                finished[0] = True
                timer.stop()
                dialog.accept()
                self.record_dialog = None
                path = (
                    Path(tempfile.gettempdir())
                    / ("chatters-voice-" + uuid.uuid4().hex + ".wav")
                    if send
                    else None
                )

                def saved(result, error):
                    self.recording_busy = False
                    if error:
                        QMessageBox.warning(self, "Recording failed", error)
                        return
                    if path:
                        if self.session == session and self.target == target:
                            self.upload_file(path, True)
                        else:
                            path.unlink(missing_ok=True)

                self.background(lambda: recorder.finish(path), saved)

            def tick():
                elapsed[0] += 1
                timer_label.setText(f"Recording… {elapsed[0]} / 60 seconds")
                if elapsed[0] >= 60:
                    finish(True)

            timer.timeout.connect(tick)
            timer.start(1000)
            layout.addWidget(button("Stop and send", lambda: finish(True), "primary"))
            layout.addWidget(button("Cancel", lambda: finish(False)))
            dialog.rejected.connect(lambda: finish(False))
            dialog.exec()

        self.background(recorder.start, ready)

    def make_call_window(self, info, title):
        if self.call_window:
            self.call_window.close()
        self.call_window = CallWindow(self.adapter, info, title, self)
        self.call_window.show()
        state = self.call_states.get(info["id"], {})
        if state.get("state") == "active":
            self.call_window.activate()
        elif state.get("state") == "ended":
            self.call_window.shutdown(state.get("reason", "Call ended"))

    def start_call(self, mode):
        if self.recording_busy:
            QMessageBox.information(
                self, "Microphone busy", "Finish the recording first."
            )
            return
        if self.call_window and not self.call_window.ending:
            self.call_window.raise_()
            return
        person = self.person(self.target)
        if not person:
            return
        self.request(
            "request_call",
            dict(recipient=person["id"], mode=mode),
            lambda data: self.make_call_window(data, person["display_name"]),
        )

    def sign_out(self):
        if self.call_window:
            self.call_window.close()
        if self.record_dialog:
            self.record_dialog.reject()
        self.session += 1
        self.adapter.close()
        self.drafts.clear()
        self.histories.clear()
        self.unread.clear()
        self.voice_cards.clear()
        self.voice_statuses.clear()
        self.state = dict(people=[], groups=[], conversations=[], online=[])
        self.login_screen()

    def closeEvent(self, event):
        if self.call_window:
            self.call_window.close()
        if self.record_dialog:
            self.record_dialog.reject()
        self.adapter.close()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Chatters")
    app.setOrganizationName("Chatters")
    adapter = NetworkAdapter()
    window = Window(adapter)
    window.show()
    try:
        return app.exec()
    finally:
        adapter.close()


if __name__ == "__main__":
    raise SystemExit(main())
