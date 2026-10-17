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
