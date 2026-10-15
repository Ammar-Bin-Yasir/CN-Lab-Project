# Chatters Final Team Project Reference

Version 1.1 — October 15, 2026. Submission: October 22, 2026 (Asia/Karachi). This is the agreed implementation baseline, not a claim of completed work. Team: Ammar, Abdullah, Ashna, and Ayesha. All four roles remain unassigned; role numbers are work packages, not assignments to people. Repository: https://github.com/Ammar-Bin-Yasir/CN-Lab-Project. The teacher's original brief controls course requirements; our supporting choices are identified separately.

## Product and success target

Build Chatters, a Python desktop LAN messenger with a Discord-inspired visual hierarchy, basic profiles, persistent conversations, groups, sharing, and one-to-one calling. Use the screenshots for structure and visual inspiration; do not reproduce their private content or Discord branding. Prioritize correctness, responsiveness, clear feedback, and a coherent design.

The teacher requires Python socket programming, threads, simultaneous clients, real-time messages, active-client display, rooms, private chat, file/image/video/voice-message sharing, and voice/video calling. We target four clients on four physical devices to satisfy the brief's inconsistent wording about three or more versus more than three devices. GUI is an example under its optional-feature rubric; the separate best-project award has no supplied scoring formula.

Our supporting choices are PySide6, profiles/login, SQLite, UDP server discovery, public/password-protected groups, persistent history, and two simultaneous call pairs. They improve usability but must not displace teacher-required functionality.

## Deployment and first use

One computer runs the server, which owns the database, retained attachments, connection registry, rooms, and call coordination. Four clients connect over the same LAN/Wi-Fi. Classmates may participate in the presentation, but first verify the core demonstration with four known working client devices. Extra participants are not a substitute for rehearsal or evidence of capacity. A server-only computer plus four client computers means five computers; with four computers, one runs both server and client. The server must remain available during communication.

Users receive a client package for the tested OS; they do not need the development repository. Developers and the teacher receive source. First verify a directory-based packaged build, retaining setup instructions and a launcher as a fallback. A standalone package must be tested on a teammate's device without the developer environment.

Login is the first main screen. Discover project servers through custom UDP broadcast in the background, show connection status, and allow server selection or manual address entry if needed. This is not mDNS and does not scan all people/devices on the Wi-Fi. Once connected over TCP, register with a unique username, password, and display name, or log in. Accounts belong to that server. Home shows connected app users; a fresh database has no groups or conversations.

## Features and acceptance criteria

| Feature | Scope and acceptance |
|---|---|
| Multi-client communication | At least four clients on four physical LAN/Wi-Fi devices work simultaneously. The server can run on one of those devices. |
| Server discovery | UDP discovery lists available project servers; manual address entry remains a fallback. Clients connect by TCP afterward. |
| Basic profiles | Register/login with unique username and password; optional display name. Returning users retain the same internal user ID. Wrong credentials fail clearly. |
| Presence | The server updates the online-user list on joins and detected disconnects. Profiles and group memberships remain when someone goes offline. |
| Text messaging | Sender and timestamp are visible. Save the message before acknowledging server acceptance; private messages route only to their recipient. |
| Groups | Create/list/join/leave public or password-protected LAN groups; any authenticated user may create one. A shared group password is checked when establishing membership; no admin roles are added. Messages route to members. Groups survive the creator leaving, all clients disconnecting, and server restarts. |
| Private conversations | Select an online profile to chat. Authenticated participants can reopen recent saved history. A different user cannot access that history. |
| Files and media | Transfer files, images, videos, and audio to people or groups. Show progress and completion/failure. Verify received-file integrity. |
| Voice messages | Record, send, and play recorded voice messages. |
| Voice calls | One-to-one, two-way live audio with request/accept/reject/end and mute controls. |
| Video calls | One-to-one live video with audio, displayed in a Qt call window with local preview and end controls. |
| Concurrency | Network/media work runs outside the GUI thread. Messages remain usable during transfers/calls; disconnects do not crash unrelated clients. |
| Persistence | SQLite stores profiles, room records/membership, messages, and attachment metadata. Reopening the server and logging in restores authorized recent text history. |

Initial team-proposed limits: files up to 20 MiB, recordings up to 60 seconds, and one active call per person, allowing independent pairs to call simultaneously. Target two concurrent call pairs with four clients. Begin video at low resolution and frame rate and measure actual results. These are design limits, not teacher-specified limits. Use headphones during calling demonstrations.


## Complete implementation stack

| Layer | Technology | Responsibility |
|---|---|---|
| Language | Python 3 | Both client and server |
| Desktop interface | PySide6, using Qt Widgets | Application windows, layouts, lists, buttons, dialogs, and conversation views |
| Styling | Qt Style Sheets, also called QSS | Consistent colors, typography, borders, padding, and widget states; CSS-like but not browser CSS |
| Optional layout tool | pyside6-designer | Visual layout editor; Python-built layouts are also acceptable |
| Networking | Standard-library socket | Real socket connections between clients and server |
| Server concurrency | Standard-library threading, locks, and queue | Per-client workers, shared state protection, outgoing queues |
| Client concurrency | Background Python threads and Qt queued signals | Network/media work outside the GUI thread; GUI updates on its main thread |
| Application protocol | Standard-library json and struct | Structured control messages and length-prefixed frames |
| Audio | sounddevice and NumPy | Capture/playback and audio buffers |
| Recorded audio | Standard-library wave | Save and load voice-message recordings |
| Video | opencv-python, with PySide6 image widgets for display | Capture, encode/decode camera frames; show received video inside a Qt call window |
| Files | Standard-library pathlib and hashlib | Save received files and verify integrity |
| Persistence | SQLite through standard-library sqlite3 | Server-side profiles, rooms, membership, and message history |
| Identity | Unique username/password, internal user ID | Recognize returning users and authorize private-history access |
| Password storage | Salted scrypt through hashlib | Store password-verification records rather than plaintext passwords |
| Server discovery | UDP broadcast through socket, with manual fallback | Find the LAN server; the server supplies user/room lists |
| Packaging | PyInstaller | A runnable desktop distribution for the selected and tested target OS |
| Development | Existing familiar editor, Git, virtual environment, dependency file | Collaborative work and reproducible setup |
| Verification | Protocol checks and scripted/manual four-device scenarios | Verify framing, routing, transfers, calling, disconnects, and package launch |

Choose and pin concrete Python/dependency versions only after testing installation and camera/audio support on the team's target OS. For this deadline, aim to support one demonstration OS first rather than promising equal polish across platforms.


## Persistent application structure

Use three primary regions: a narrow navigation rail, a context sidebar, and a flexible main panel. The rail always contains Home, joined group shortcuts, Create Group, and Browse Groups. Use group initials and tooltips rather than requiring uploaded group images. Show a selection marker and unread dot/count. Keep the current user's name and connection status accessible at the bottom of navigation.

| Mode | Context sidebar | Main panel |
|---|---|---|
| Home | Online People action and saved private conversations | Online-user directory with names, presence, and Message actions |
| Private conversation | Same Home navigation and private-conversation list | Selected person's header/status, voice/video actions, saved messages, and composer |
| Group conversation | Group name, public/password-protected label, member list/presence, and Leave action | Group header, saved group messages, and composer |

Home returns to the online-user directory. Selecting a private conversation stays within Home context. Selecting a joined group changes the sidebar and conversation together. The private-conversation list is not shown in group context. Do not add Discord's channel hierarchy or a permanent fourth activity/profile panel.

## Visual language

Use layered charcoal surfaces: darkest navigation rail, a slightly lighter sidebar, and a distinct conversation surface. Use a purple-blue accent for primary actions and selected states. Favor flat surfaces, subtle separators, restrained corner radii, and readable neutral text. Keep secondary timestamps quieter without making them illegible.

Use compact initials avatars, sender names, timestamps, and left-aligned message rows inspired by the references. Group consecutive messages from the same sender where helpful, retaining clear boundaries between people and times. Do not force message bubbles if they make the reference-inspired layout less coherent. Use one consistent icon style, accessible tooltips, and keyboard-focus states. Do not rely on color alone for status.

The conversation header identifies its person/group. The composer stays at the bottom and provides attachment, recorded voice, text input, and send actions. Keep voice/video calling in the private-conversation header, since group calls are outside scope. Render calls in a dedicated Qt call window.

## First use and empty states

Login is the first main screen. Discover the server in the background; expose selection or manual connection when needed. Show registration as a secondary action. After login, open Home.

A new database has no pre-created groups. The rail shows Home and group actions; the private list explains how to start a conversation; the main panel shows currently connected app users. Returning users see saved memberships and conversations. No users online produces a clear empty state and connection status rather than a blank panel.

## Group access

Any authenticated user can create a public or password-protected group. Creation asks for a name, access type, and password when applicable; the creator becomes a member. Browse lists groups with a lock where appropriate. A correct password grants persistent membership; returning members do not re-enter it. Leaving removes membership, and rejoining a protected group requires its password again.

This is a reusable shared password, not a single-use code. There are no admin roles, kicking, password changes, or ownership transfer. Groups persist when the creator/all members disconnect. Store password-verification hashes rather than readable group passwords. Only authorized members receive messages or history. All group members may view the group's saved history in this initial model; make that join behavior clear. Group metadata can be listed, but messages are not previewed before joining.

## Calling and feedback

Allow independent simultaneous one-to-one calls, with one call per person. Target two concurrent call pairs with four clients. Show busy, incoming, connecting, active, ended, and failed states. Calls require distinct server-side call IDs and isolated routing/queues so one call's teardown cannot end another.

Keep transfers and network activity responsive. Show transfer progress, recording duration/cancel/send, connection loss/retry, and message failure clearly. Incoming messages should not pull the reader away from older history; provide an unread/new-message indication. Saved-history loading, login errors, and group-password errors must have intentional states.

## Scope discipline

Borrow the reference hierarchy and styling, while using our own name and assets. No friends/request system, shop, subscriptions, activities, bots, reactions, rich profile pages, channel hierarchy, or group calls are added by these references. Prototype Home, private chat, and group chat at the actual demonstration window size before polishing individual controls.

## Persistence and authorization

Use SQLite on the server via sqlite3. Store users, rooms with access type and optional password hash, memberships, messages, and attachment metadata. Save media files under a managed server storage directory; do not record live calls. Use internal IDs, not display names, as keys. Usernames are unique; normalize consistently before uniqueness checks. Store salted password-verification hashes for user and group passwords.

A dedicated database worker owns its SQLite connection and processes queued requests. Use parameterized SQL and transactions. Commit a message before confirming server acceptance. Only the two participants may retrieve a private conversation; only current members may read group history or send to that group. New members may view the group's saved history, and the join UI should disclose that behavior. Leaving revokes future server access; it cannot retract material already downloaded.

Persist memberships independently of online presence. Groups remain when their creator or every client disconnects. There are no administrator permissions, kicks, ownership transfers, or post-creation group-password changes. A shared group password is reusable and entered when establishing membership, not each login. Rejoining after leaving requires it again.

Initially allow direct sends only to online recipients; show saved conversations when recipients are offline and disable sending/calling appropriately. Saved history is not an offline-delivery guarantee. Load the latest 50 messages initially; older-history pagination can follow only after core behavior works. Unread indicators are session-level unless explicitly persisted later.

## Communication architecture

Qt widgets live on the GUI thread. Networking and media run in background workers and communicate with the GUI using queued Qt signals. Never block the GUI on recv, file I/O, or camera/audio work. The server uses client workers, protected shared state, and serialized writes per connection.

Use explicit length-prefixed TCP framing; handle fragmented headers/bodies, combined messages, disconnects, and payload limits. JSON carries control data; binary attachment/media data uses dedicated framed channels. Keep bulk and live media off the chat/control connection. Each extra channel must be bound to an authenticated session and authorized transfer/call; a claimed user ID is not sufficient.

Initial live media uses separate framed TCP channels with bounded buffers. TCP loss recovery can increase media delay, so validate early on actual devices and document observed limitations. OpenCV/sounddevice handle capture/playback, while our code implements streaming and signaling. Render video through Qt. Calls have unique IDs, isolated routing/queues, one active call per person, and two concurrent pairs as the demonstration target. Reject busy/invalid participants, clean up on timeout/disconnect, and never let one call's cleanup affect another.

Before parallel feature work, agree on the minimal contract in INTEGRATION_CONTRACT.md. Freeze each feature's contract before separate implementation; update consumers together if it changes.

## Scope boundaries

No web app, cloud deployment, phone/email verification, recovery flow, profile-photo uploads, friend requests, channel hierarchy, group calls, screen sharing, bots, reactions, advanced search, or offline notifications. TLS is outside the current commitment. Password hashing protects stored credentials, not network traffic; make no end-to-end encryption or production-security claims. Use demonstration credentials, not reused personal passwords.

Proposed file limit: 20 MiB. Proposed recording limit: 60 seconds. Start video around 320×240 and 10 fps, treating these as tunable prototype targets rather than measured guarantees. Test with headphones and working camera/microphone permissions. Basic file opening can use the OS viewer; a complete video-file player is outside scope.

## Deliverables

1. Working server and desktop client, tested launcher, and verified package where feasible.
2. Source repository, tested dependency versions, configuration examples, synthetic sample media, and an identified submission commit.
3. Installation/user guide: server startup, LAN/discovery fallback, profiles, groups, media devices, controls, storage, and troubleshooting.
4. This scope/design reference plus protocol documentation, SQLite schema, architecture and sequence diagrams.
5. Final report in PDF format: objectives, requirements, actual implementation, screenshots, test evidence, observed performance, limitations, references, and contributions.
6. Test results with expected/actual behavior, device/network setup, and honest failed/untested status.
7. Slides sized to the presentation slot, with a section for each member.
8. Four-device demo checklist, assigned speaking parts, sample files, and a short backup recording.
9. Contribution log and final submission checklist.

## AI use and report format

According to Ammar, there is no explicit prohibition on AI assistance; each member must understand and explain the project. Apply the shared AI rules and understanding checks. The final report must be a PDF; page count, template, and other formatting details are not yet supplied. Keep editable report source alongside the exported PDF. Do not write implementation results before they are verified.

## Working schedule from October 15

No implementation is assumed complete. These are target checkpoints; report actual progress daily.

| Date | Checkpoint |
|---|---|
| Oct 15 | Assign roles/OS; initialize repo and shared contracts; two-client framed text; Qt layout sketch; test microphone/camera access. |
| Oct 16 | Four-client presence; basic profiles, SQLite, private/group routing; prove two-device live-media path and integrate a minimal Qt client. |
| Oct 17 | Persistent history, discovery/fallback, files and recordings; working two-way audio call. |
| Oct 18 | Video with audio, protected group joins, and complete primary UI paths. |
| Oct 19 | Integrated four-device test; verify two concurrent call pairs, authorization, restart persistence, and failure handling. |
| Oct 20 | Fix failures; visual consistency; package/launcher check; assemble report and slides. |
| Oct 21 | Feature freeze; final results, backup recording, complete rehearsal and submission check. |
| Oct 22 | Smoke check and submit/present by the confirmed time. |

Write docs and collect screenshots daily. If late, drop decorative work and single-file packaging before required features. Do not silently remove requirements; surface blockers immediately. Media feasibility receives early attention from the most experienced member and media owner together.

## Team coordination and decisions still needed

See TEAM_WORKFLOW.md for ownership and GitHub practices, members/ for personal guides, AGENTS.md for AI instructions, and CHECKLIST.md for unresolved decisions and release gates. Once copied into GitHub, this document is the source of truth; older discussion drafts are superseded. Any change to scope, protocol, schema, dependencies, or module boundaries requires team coordination and an updated document.
