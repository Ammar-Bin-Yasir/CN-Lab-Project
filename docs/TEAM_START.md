# Team start — October 16

This is the starting map for the actual Chatters project. The desktop interface is reusable product work; its local data provider is temporary. There is no separate second application to rebuild from scratch.

## Roles — confirm October 17

Team: Ammar, Abdullah, Ashna, Ayesha. Names intentionally remain unassigned.

| Package | Owner | Reviewer | Starting guide |
|---|---|---|---|
| 1 · Networking/integration | Unassigned | Unassigned | [Networking](members/01_networking_integration.md) |
| 2 · Desktop UI | Unassigned | Unassigned | [UI](members/02_desktop_ui.md) |
| 3 · Data/groups/files | Unassigned | Unassigned | [Data](members/03_data_groups_files.md) |
| 4 · Audio/video | Unassigned | Unassigned | [Media](members/04_audio_video.md) |

Fill this table together. Ownership means responsibility for coordination, tests and explanation; everyone may ask for help. Confirm target OS, collaborator access and working audio/video devices at the same time.

## Everyone's first 30 minutes

1. Clone the repository and follow the root README. Until the foundation is merged, check out feature/desktop-preview to inspect it. Do not all commit onto that shared branch.
2. Run `python run.py --demo`. Create a protected group, leave it, fail a password attempt and rejoin. Restart and inspect saved history.
3. Run `python -m pytest -q`. Record any setup failure, OS and Python version.
4. Read AGENTS.md, FINAL_PLAN.md, INTEGRATION_CONTRACT.md and your assigned guide.
5. Create one small task with the issue template. Fill owner, paths, dependency and success/failure checks before coding.

Use synthetic data. Local preview accounts/groups are not eventual server accounts/groups; there is no promised migration.

## First tasks and boundaries

### Package 1 — prove framed transport

Work in `shared/`, `server/transport/`, `client/network/`, and `tests/network/`.

First agree and document the text-only envelope, size cap, response/error fields and IDs in INTEGRATION_CONTRACT.md. Then implement length-prefixed send/read helpers and a two-client transport harness. This is a transport experiment, not a shortcut around production authentication. Test fragmented headers/bodies, multiple frames in one stream, oversize frames and disconnect mid-frame. Keep GUI changes coordinated with package 2.

Deliver: runnable two-client harness, tests, exact request/response examples, and instructions. No media dependency is needed.

### Package 2 — understand and prepare the existing UI

Work in `client/ui/`, synthetic `screenshots/`, and `tests/ui/`.

Start by tracing Send from button to local adapter and back to rendering. Add a focused regression test for drafts across private/group switching. With package 1, define the adapter's pending/result/error events, then implement connection status and pending/failed send states. Keep these states driven by real adapter events once available. Do not add more Discord features or alter the socket protocol alone.

Deliver: tested UI change, before/after screenshot, and agreed adapter handoff. Existing `client/app.py` is a compatibility import, not the place for new screens.

### Package 3 — establish server identity and storage

Work in `server/storage/`, `server/services/`, and `tests/storage/`.

First design and document users, groups, memberships and messages with stable IDs and constraints. Implement the database worker/connection ownership, parameterized operations, unique username normalization and salted password verification. Use temporary databases in tests. Do not copy the demo schema as the production schema: private/group authorization and server identity need real ownership checks.

Deliver: schema, worker lifecycle, registration/login success and failure tests, duplicate username check and restart persistence. Then coordinate authorized messaging/history with package 1; attachments come after this foundation.

### Package 4 — prove devices early

Work in `client/media/` and `tests/media/`; coordinate server signaling with package 1 and call widgets with package 2.

Start with a local microphone recording/playback and camera-preview experiment. Agree and add only needed pinned audio/video dependencies after installation on the demo OS. Keep capture outside the GUI thread, bound recording duration, and release devices on close/error. No network or fabricated remote participant is needed for this first check.

Deliver: reproducible device-check command, actual device/OS results, permission/missing-device handling and clean shutdown. Record measured results honestly. Then agree audio format, video encoding, channel binding and call IDs with package 1 before streaming.

## First shared milestone

Two real clients on two devices authenticate to a server, exchange one private text message, display it in the existing UI and retrieve authorized saved history after reopening. This milestone combines packages 1–3; package 4 performs device checks in parallel. It is not complete when the local demo works.

Integrate small pieces daily; do not wait for all modules to be finished. The required final baseline remains four physical clients and the full feature list in FINAL_PLAN.md.

## Daily handoff

Use [HANDOFF_TEMPLATE.md](HANDOFF_TEMPLATE.md). Each person owns their tests, report notes and a short explanation. Ask for an interface decision before changing another package's contracts. Do not invent mutually incompatible message formats in separate AI sessions.

The Oct 15 checkpoints were planned targets, not completed implementation. As of Oct 16, only the local desktop foundation is verified. Reassess the remaining schedule at role assignment; preserve the required networking/media work before decorative polish.
