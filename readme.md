# Chatters

Python/PySide6 desktop LAN chat. One server owns accounts, groups, history and attachments. Clients connect with usernames; no browser is involved.

## Setup

Use Python **3.12**. On Linux/macOS:

```sh
python3.12 -m venv .venv-live
source .venv-live/bin/activate
```

On Windows PowerShell:

```powershell
py -3.12 -m venv .venv-windows
.\.venv-windows\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-windows\Scripts\python.exe run.py
```

On Linux/macOS, with the environment activated, install:

```sh
python -m pip install -r requirements.txt
```

All desktop/media dependencies are pinned. Audio requires PortAudio (for example the portaudio package on Fedora or libportaudio2 on Debian/Ubuntu); sounddevice includes support libraries on some platforms. Camera and microphone permissions/devices must be available. The server itself uses only Python's standard library and does not require Qt or media packages.

## Start the server

On one computer, from the repository root:

```sh
python run_server.py
```

Defaults: TCP 5050 for chat, TCP 5051 for file transfers, TCP 5052 for call-session setup/lifetime, UDP 5052 for live audio/video, and UDP 5051 for discovery. TCP and UDP may share a port number. Allow these ports in the host firewall for the demonstration LAN. Devices need to reach one another; some campus/guest Wi-Fi isolates clients. If needed use a trusted hotspot/router that allows local traffic.

Server options: `--host 0.0.0.0 --port 5050 --data runtime`. Files use the next TCP port; calls use the second next port over both TCP and UDP. `--no-discovery` disables UDP advertising. Stop with Ctrl+C. Accounts and history remain under the selected data directory; attachment files live under its files/ folder. Back up the entire directory together, not just SQLite. Use a fresh data directory for a clean demonstration.

## Start each client

```sh
python run.py
```

Click Find LAN server or enter the server's local address, such as `192.168.1.10:5050`, and Connect. `127.0.0.1:5050` works only when client and server run on the same computer. Register a unique account or log in. Registration also signs in. One active connection per account is allowed, so use a different account on each demonstration client.

Home lists other connected app users. Select someone to start a private conversation. Enter sends; Shift+Enter creates a new line. Private text is saved even when the registered recipient is offline; they can open the conversation after login to retrieve recent history. Select All on the People screen to start such a conversation. Files and live calls still require an online recipient. Existing conversations/history remain visible after people disconnect.

Use + in the rail to create a group and the browse button to join one. Protected groups have a reusable shared password. Membership and groups survive restarts. New members can read saved group history; leaving revokes access. There are no admin roles.

Use Emoji beside the composer to choose a Unicode emoji. It inserts at the cursor or replaces selected text; it does not send automatically. Emojis travel and persist as normal text in private/group messages, including offline private text. You can also paste emojis. Linux uses the bundled color emoji font; monochrome is used only if that font cannot load. Windows/macOS keep native emoji rendering. GIF-viewer tooling remains on the separate experimental branch.

Use + beside the message input to send a file up to 20 MiB. Save attachment downloads and verifies a file; nothing executes automatically. Record creates a voice message of up to 60 seconds; Stop and send uploads it, Cancel discards it. Recordings appear as compact voice cards: Play downloads/plays the audio, and the download arrow saves it as voice-message.wav. Playback status and duration appear after loading. Voice/video calls are one-to-one; accept/reject from the incoming prompt, mute/end in the call window. Use headphones. Other pairs may call independently.

A server acknowledgement means saved/accepted, not read by the recipient. After a timeout/disconnect the outcome of a pending write can be uncertain: reconnect, log in and inspect history before retrying. Clients do not silently replay messages. No cloud service, TLS or end-to-end encryption is implemented; use demonstration credentials, not personal reused passwords.

## Ownership and reading order

| Person | Main code |
|---|---|
| Ammar | client/ui/, client/network/{adapter,connection,discovery}.py, client/media/, shared/protocol.py, server/storage/, services/{auth,calls}.py, transport/discovery.py |
| Abdullah | server/transport/{listener,connection,registry}.py |
| Ashna | server/services/{messaging,groups}.py, coordinating storage with Ammar |
| Ayesha | client/network/files.py, server/services/files.py, coordinating attachment metadata with Ammar |

Read run_server.py → listener.py → connection.py for the server and run.py → ui/app.py → network/adapter.py → network/connection.py for the client. Services apply permissions; only the database worker accesses SQLite. Protocol details and current verification evidence are in docs/INTEGRATION_CONTRACT.md. Tests/screenshots remain outside Git as requested.

## Verification limits

Local tests exercise four real TCP clients, authentication/access failures, persistent text/groups, binary transfers, two simultaneous call pairs with synthetic media packets, discovery, and two real offscreen Qt clients. Local hardware checks also opened microphone/speaker, recorded/played a short sample, captured a camera frame, and exercised the actual media workers through the local relay. Audio was muted during call tests to avoid feedback; no captured content was retained. This is not evidence of four physical laptops or acceptable end-to-end call sound/video quality. Verify those on the actual demonstration setup before submission. Device-specific failures are shown in the UI; do not claim unavailable media works.

## Repository layout

- `run.py`: desktop client entry point; imports the interface from `client/ui/app.py`.
- `run_server.py`: server entry point.
- `client/ui/`: windows, voice cards, call dialog and QSS styling.
- `client/network/`: adapter, control connection, discovery and file-transfer client.
- `client/media/`: audio, video, recording and media transport.
- `server/transport/`: listeners, client handlers, session registry and discovery.
- `server/services/`: authentication, messages, groups, files and call coordination.
- `server/storage/`: SQLite worker and data operations.
- `shared/`: control framing/request validation and the UDP media packet codec used by both programs.
- `docs/`: current project scope, protocol and team reading guide.

`__init__.py` marks a Python package; some also expose imports such as AccountStore. `__pycache__/` contains automatically generated bytecode, is ignored by Git, and may reappear after running Python. Runtime data, virtual environments, recordings, tests and screenshots are not committed.

### Windows audio setup check

Install dependencies on every computer running a client, using the same interpreter that launches it. From the project directory:

```powershell
.\.venv-windows\Scripts\python.exe -c "import sounddevice, cv2; print(sounddevice.query_devices())"
```

If this fails, correct that client environment before testing LAN calls. Allow microphone/camera access. Text chat uses TCP 5050; files use 5051; call setup uses TCP 5052 and live media uses UDP 5052. Allow both protocols on the server firewall. A working text connection does not verify file/media reachability.

## UDP calls

Update the server and every client together: this media protocol is incompatible with the previous TCP-media version. Call request/accept/end still use TCP chat control. A separate TCP session on the media port authenticates the participant and issues fresh, memory-only UDP credentials; it remains open to detect disconnects. Live samples and JPEG fragments travel only over UDP through the server. Recorded voice messages and files still use TCP.

Datagrams are at most 1,200 bytes. Audio has a small 60 ms playout buffer; missing/late blocks become silence. JPEG frames are split into numbered fragments; incomplete frames expire after 350 ms. Signed packets, replay checks, endpoint binding, bounded reassembly and per-sender relay rate limits restrict malformed traffic. UDP registration/heartbeats detect unreachable media and lost connections. No lost media is retransmitted. This is a custom LAN media protocol, not RTP/WebRTC; no adaptive bitrate, audio compression, echo cancellation or congestion control is implemented.

Signatures authenticate packets using credentials exchanged over plaintext TCP. They do not provide encryption or protection from someone intercepting that exchange. Use this on a trusted LAN with demonstration data. Separate-device audible quality and Windows firewall/device behaviour still need a LAN rehearsal.

## Emoji font

Linux clients bundle the unmodified Noto Color Emoji bitmap font from [Google Noto Emoji v2.047](https://github.com/googlefonts/noto-emoji/tree/v2.047/fonts), licensed under the SIL Open Font License 1.1 (client/ui/assets/OFL.txt). It avoids blank COLRv1 glyphs on affected Qt builds. Windows/macOS retain native emoji fonts. Keep the assets folder when distributing the source; no font download or system installation is needed at runtime.
