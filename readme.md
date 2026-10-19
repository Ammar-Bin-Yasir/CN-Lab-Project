# Chatters

Python desktop LAN chat project. Submission: October 22, 2026.

## Run the current local preview

Use Python 3.12. From the repository root:

```sh
python -m venv .venv
```

Activate with `source .venv/bin/activate` on Linux/macOS, or `.venv\Scripts\Activate.ps1` in Windows PowerShell. Then:

```sh
python -m pip install -r requirements.txt
python run.py --demo
```

Choose Explore preview. Profiles, messages and groups are stored locally outside this repository. The UI is implemented; LAN/server communication, real file delivery and live calls are not implemented yet. The temporary demo adapter will be removed after real client/server flows work.

## Team

| Person | Ownership |
|---|---|
| Ammar | Desktop UI, integration, network adapter, accounts/storage, discovery, live audio/video |
| Abdullah | Server connections, client workers, presence and disconnect handling |
| Ashna | Private/group text routing and membership checks, coordinated with Ammar's storage |
| Ayesha | File-transfer channels, bounded chunks, checksums and interruption handling |

Start with [team tasks and call guide](docs/TEAM_START.md), [workflow](docs/TEAM_WORKFLOW.md), [protocol agreement](docs/INTEGRATION_CONTRACT.md) and [full scope](docs/FINAL_PLAN.md). Follow AGENTS.md when using AI.

Screenshots, test tooling and evidence are maintained locally by Ammar. Verification is still required for every change; include commands and actual results in your PR. There is no automated test suite distributed in this minimal checkout.

## Server account storage (implemented separately)

`server/storage/accounts.py` now provides a worker-owned SQLite account store with registration and password verification. Its API and handoff are in [INTEGRATION_CONTRACT.md](docs/INTEGRATION_CONTRACT.md#implemented-account-storage-boundary--october-19). This is not yet connected to a server listener or the desktop login screen. Preview accounts remain separate.

## Component ownership map

Files marked PLACEHOLDER contain documentation only; importing or executing them does not implement the described behaviour. File names mark work boundaries, not frozen function signatures. Empty __init__.py files make folders Python packages.

```text
run.py                         Ammar — current desktop launcher
run_server.py                  Ammar + Abdullah — planned server launcher
shared/protocol.py             Ammar coordinates — common wire format
client/
  ui/app.py, theme.qss          Ammar — existing interface
  ui/call_window.py            Ammar — call interface
  demo/                        Temporary local preview; remove after integration
  network/connection.py        Ammar — background socket client
  network/adapter.py           Ammar — Qt request/result bridge
  network/discovery.py         Ammar — find servers
  network/files.py             Ayesha — client file transfers
  media/audio.py, video.py     Ammar — microphone/speaker/camera
  media/recording.py, calls.py  Ammar — recorded/live media
server/
  transport/listener.py        Abdullah — accept clients
  transport/connection.py      Abdullah — per-client I/O
  transport/registry.py        Abdullah — connections and presence
  transport/discovery.py       Ammar — discovery replies
  services/auth.py             Ammar — authentication/session integration
  services/messaging.py        Ashna — private/group text routing
  services/groups.py           Ashna — group operations
  services/files.py            Ayesha — server file transfers
  services/calls.py            Ammar — call coordination
  storage/accounts.py          Ammar — implemented account worker
  storage/conversations.py     Ammar — group/message persistence
  storage/attachments.py       Ammar — attachment metadata
```

Storage placeholders must extend/use the existing worker rather than creating competing SQLite workers or connections. Ashna and Ayesha coordinate storage API needs with Ammar; Abdullah coordinates authentication binding with Ammar. The current UI remains in app.py; extra screen files are unnecessary until the implementation needs them. Tests and screenshots remain outside this repository.
