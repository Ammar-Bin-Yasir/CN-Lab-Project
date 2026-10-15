# Chatters desktop preview

A real PySide6 desktop interface for the team's LAN messenger. This build is the **local UI phase**, not the finished networking project. It uses clearly labelled sample contacts; it does not discover users or send data to other computers.

## Run

Use Python 3.12. From the repository root:

```sh
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python run.py --demo
```

Choose **Explore preview**, or create a local profile with a username and a password of at least eight characters. These are preview credentials, not your eventual server account. Qt stores preview.sqlite in the OS application-data folder for Chatters/ChattersPreview. No runtime data goes in the repository.

## Working now

- Dark desktop layout with group rail, Home/private sidebar and group-context sidebar.
- Local registration/login, salted password hashes and validation.
- Searchable sample people, saved private conversations and selectable literal message text.
- Enter to save locally, Shift+Enter for a newline, session drafts retained during navigation.
- Public/protected group creation, browsing, joining, leaving and saved group history.
- Wrong-password errors and membership checks. Shared passwords are reusable, not OTPs.
- File picker and 20 MiB validation, with an explicit preview-only result.

Initially there are no groups or messages. Sample contacts use teammates' first names and are not live presence. Explore preview shares one demo identity. Local profiles share group records; private preview histories are separate.

## Pending integration

Sockets, discovery, authoritative server/database worker, live presence, server authentication, delivery acknowledgements, incoming messages/unread counts, file transport/progress, recording/playback, microphone/camera capture, call signaling/media, reconnect and executable packaging. Disabled call controls cannot start a fake call. This build does not yet satisfy the networking submission requirements.

## Code map

- client/ui/app.py: Qt screens, forms and interaction handling.
- client/ui/theme.qss: styling and focus states.
- client/demo/service.py: disposable local preview adapter, not the server schema.
- run.py: entry point.
- tests/test_preview.py: persistence, account isolation, group access, navigation and keyboard checks.

The UI never executes SQL directly. The preview service is synchronous for small local operations. **Do not replace these methods with blocking socket calls.** Introduce a background client adapter with queued Qt signals, then update handlers to pending/success/failure states. Replace sample contacts with server presence and local history with authorized server results. Agree payloads using INTEGRATION_CONTRACT first.

## Verify

```sh
python -m pip install pytest
QT_QPA_PLATFORM=offscreen python -m pytest -q
```

On Windows set QT_QPA_PLATFORM in your shell before running pytest. A real desktop/device check is still required before PyInstaller packaging.

For the first review, create a protected group, leave, try a wrong password, rejoin, restart and check history. Decide layout changes before integrating networking. Be able to explain why the UI uses an adapter and why this local database cannot serve as the shared LAN database.
