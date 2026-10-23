# Chatters final project scope

Chatters is the Computer Networks desktop LAN project for Ammar-Bin-Yasir, Ashna-Simi-Butt, Hafiz Muhammad Abdullah Aamir and Ayesha Zulqarnain. The report is submitted as PDF. Current roles are in TEAM_START.md and the implemented protocol is in INTEGRATION_CONTRACT.md.

## Architecture and stack

One Python 3.12 server owns SQLite data, uploaded files and live sessions. PySide6 desktop clients communicate through it. Qt Widgets/QSS provide the dark interface; standard-library sockets, threading, queue, json and struct provide networking and concurrency. sounddevice provides audio, NumPy supports media arrays and OpenCV captures/encodes video. Exact versions are pinned in requirements.txt. No web interface is used.

TCP 5050 carries control requests/events, TCP 5051 carries files, TCP 5052 authenticates call sessions, UDP 5052 carries live media, and UDP 5051 provides custom server discovery with manual-address fallback. The server can run alongside a client on one laptop.

## Implemented scope

- Unique username/password accounts, optional display names, salted scrypt verification and one session per account.
- People directory with All/Online tabs and name/username search, independent of shared groups.
- Persistent public profiles with editable display name, bio, picture and banner color. Usernames remain fixed. Existing accounts gain default profiles automatically. In-app profile, group, call, emoji and recording dialogs use integrated close controls without native title bars; the profile banner spans the dialog edge to edge behind its avatar.
- Persistent private text, accepted for registered offline recipients. Recipients retrieve saved recent history after login. No delivery/read receipts or automatic retry of uncertain writes.
- Public or reusable-password groups with persistent membership, create/join/leave and authorized history. No admin roles or nested channels.
- File/image/video/audio attachments up to 20 MiB with session checks, bounded transfer and SHA-256 verification. Private uploads require an online recipient. Chats show images as inline previews, videos with an inline poster and play control where Qt's media backend supports the format, and other files as named cards with size and Save action. Preview downloads use the authorized file channel and a bounded temporary cache.
- WAV voice recordings up to 60 seconds with compact Play/Save cards. Generated storage names are hidden in the voice UI; duration is shown after loading. No seek/pause or waveform feature is claimed.
- Independent one-to-one voice/video call pairs, one call per user, with accept/reject/mute/end. Live media uses signed UDP datagrams, bounded video fragments and a small audio jitter buffer; TCP retains authentication and call lifetime. Video uses small JPEG frames; audio uses 16 kHz mono signed 16-bit PCM.
- Background network/media workers and one SQLite-owning database worker keep I/O outside the Qt thread.

## Interface

A permanent navigation rail contains Home, joined groups, Create and Browse. Home/private context shows private conversations; a selected group replaces the context sidebar with group information and members. The main panel contains people or chat history and its composer. The scrollable rail uses 52px group buttons; context lists scroll above a compact account card. Click the account card to edit your profile or sign out. People and message avatars open user profiles; group members can open a profile and start a private conversation. Calls use a separate dialog. Discord is visual inspiration only. Profile editing uses a scrollable body and fixed action footer. Group discovery includes local name search, explicit Join/Open actions, and inline request failures; protected groups use a password dialog. Calls show a dedicated voice/video stage with a local camera inset, connection status, mute and end controls. Escape ends the call, and incoming prompts close when the call ends.

## Persistence and limits

Keep the selected runtime directory to retain accounts, memberships, messages and attachment files. Session tokens, connections and calls are memory-only. History returns up to 50 recent messages within a 48,000-byte JSON budget; complete archive pagination is outside scope. The server must be available to accept messages.

Transport is plaintext: no TLS, end-to-end encryption, cloud synchronization or production-security claim. Use demonstration credentials and data. A local Unicode emoji picker is included; GIF-viewer tooling remains an unmerged experiment. Source execution is the verified distribution; standalone packaging and cross-platform call quality are not certified.

## Verification and presentation

Tests and screenshots are kept locally outside Git. Local checks cover actual TCP clients, authentication, permissions, persistence, offline text, binary files, concurrent synthetic call pairs, Qt interactions, device access and recorded voice. Real call-worker tests used muted audio; these do not establish audible speech quality across laptops. Rehearse four accounts on the actual LAN, including files, recording/playback, audible voice/video, independent pairs and server restart.
