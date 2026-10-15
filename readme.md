# Chatters

A Python desktop LAN messenger for our Computer Networks project. Team: Ammar, Abdullah, Ashna and Ayesha. **Roles are unassigned. Submission: October 22, 2026.**

## Start here

1. Read [Team start](docs/TEAM_START.md).
2. Run the preview below and explore the existing interface.
3. Choose your work package after roles are confirmed; follow its first task.
4. Use the issue/PR templates and [AI task prompt](docs/AI_TASK_TEMPLATE.md) for small changes.

## What works today

The PySide6 desktop preview has Home/private/group navigation, local profile registration/login, local persistent messages, drafts, public/protected groups, and file selection/size checks. Four preview tests verify storage and UI behaviour. Sample contacts are not connected people.

**The network product is not implemented yet.** Socket transport, server persistence/authentication, presence/discovery, file delivery, recording and live calls are pending. New folders contain handoff guides, not working implementations. See [final scope](docs/FINAL_PLAN.md).

## Run the desktop preview

Use Python 3.12 (tested here with 3.12.15) from the repository root:

```sh
python -m venv .venv
```

Activate on Linux/macOS:

```sh
source .venv/bin/activate
```

Or Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Then:

```sh
python -m pip install -r requirements-dev.txt
python run.py --demo
```

Select **Explore preview** to avoid registering. It saves only to this computer's application-data directory. Running without `--demo` reports that the network client is not ready, rather than silently launching a simulation. Python and dependencies are needed for now; no executable has been packaged.

## Verify

```sh
python -m pytest -q
```

The current tests select Qt's offscreen platform themselves. They do not prove LAN, microphone/camera, or Windows support. Real device checks are still required.

## Where work goes

| Area | Path | State |
|---|---|---|
| Desktop UI | client/ui/ | Existing working preview screens and theme |
| Temporary preview data | client/demo/ | Local-only adapter and SQLite; replace during integration |
| Client networking | client/network/ | Starter guide |
| Server transport | server/transport/ | Starter guide |
| Shared protocol | shared/ | Contract checklist; no frozen wire schema yet |
| Server storage and services | server/storage/, server/services/ | Starter guides |
| Audio/video | client/media/ | Starter guide |
| Tests | tests/ | Preview tests plus ownership guide |

The production UI should receive results from a background network adapter through Qt signals. Do not replace local service calls with blocking sockets. See [integration contract](docs/INTEGRATION_CONTRACT.md) and [handoff notes](docs/DESKTOP_PREVIEW.md).

## Collaboration

Roles will be filled in [Team start](docs/TEAM_START.md), not guessed from guide numbers. After this foundation is reviewed and merged, branch from updated main for each task. Keep changes small, obtain one review, and record test evidence and contributions. Do not push databases, passwords, private media or virtual environments.
