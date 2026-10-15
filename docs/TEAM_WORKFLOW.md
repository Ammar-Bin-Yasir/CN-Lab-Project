# Team Ownership and GitHub Workflow

## Team and ownership

Project: Chatters. Team: Ammar, Abdullah, Ashna, Ayesha. All assignments remain open. The labels Member 1–4 below identify proposed roles, not named people. Choose based on availability and interest, with the strongest networking support paired on media.

Repository: https://github.com/Ammar-Bin-Yasir/CN-Lab-Project

## Proposed responsibility split

| Role | Primary ownership | Integration partners |
|---|---|---|
| Role 1 — Networking and Integration (unassigned) | Server transport, discovery, presence, client networking adapter, shared protocol, integration/release | All members; pair early with Member 4 |
| Member 2 | PySide6 screens, QSS/theme, UI event handling, user guide/screenshots | Member 1 adapter; Member 3 data actions; Member 4 call/record controls |
| Member 3 | Database worker/schema, account and membership logic, message persistence/authorization, file-transfer service | Member 1 routing and socket channels; Member 4 recordings use file service |
| Member 4 | Audio/video capture/playback, recordings, call lifecycle/media streams | Member 1 session routing; Member 2 call UI; Member 3 file service |

Ownership coordinates edits, not exclusive knowledge. The integration owner must not become the only person who can integrate or explain the app. Member 3 has substantial work: implement identity/storage before attachments and pair with the networking owner for transfer integration. Member 4 must not work alone on media feasibility. Everyone writes tests and report notes for their feature and reviews a teammate's work.

## Proposed repository structure

```text
client/ui/             Member 2
client/network/        Member 1
client/media/          Member 4
server/transport/      Member 1
server/services/       Member 3; call service coordinated with Member 4
server/storage/        Member 3
shared/                Member 1 coordinates protocol/types/config
assets/                Member 2
scripts/               launch/package scripts; coordinated
tests/                each owner tests their behavior
docs/                  shared plan, contracts, report/test notes
AGENTS.md              shared AI rules
readme.md              verified install/run instructions
requirements.txt       agreed, tested dependencies
.gitignore             excludes runtime and private data
```

## Repository setup

The repository has been created at the URL above; its current visibility is public. Confirm that Abdullah, Ashna, and Ayesha have accepted collaborator invitations; this has not been verified. Use main as the stable branch. Commit the planning packet, ignore rules, and minimal skeleton first. Confirm a common target OS and Python/dependency versions after an installation smoke check. Do not assume a skeleton or scripts exist until created and tested.

Ignore virtual environments, caches, databases/journals, credentials, local config containing secrets, logs, downloads, recordings, build/dist output, and real personal media. Commit synthetic fixtures and configuration examples. Never commit API keys, user/group passwords, server session tokens, or the reference screenshots' private content.

## Daily working loop

1. Start with a short check-in: what works, today's small task, blockers, and shared changes needed.
2. Create a GitHub issue with owner, behavior, dependencies, affected files, and acceptance checks.
3. Branch from current main, for example feature/login-screen or fix/file-disconnect.
4. Implement one reviewable change. Keep working snapshots and test actual behavior.
5. Open a pull request describing the problem, behavior, tests run, remaining limitations, and screenshots for UI changes.
6. Get one teammate's review. Merge only once the feature's checks and relevant smoke test pass. If branch protection is unavailable, follow this manually.
7. Pull main and integrate daily. Record the tested commit, short result, and contribution. Never defer all integration until the last day.

Do not force-push shared branches, rewrite teammates' work, or change another owner's interfaces without coordinating. AI should not merge or push unless the human assigned that action. Resolve shared-file conflicts together. A merge conflict is not a reason to discard one person's changes blindly.

## Review and release

Rotate reviewers: 1 reviews 4, 4 reviews 3, 3 reviews 2, 2 reviews 1; request additional help when a reviewer cannot assess a change. Reviewers should run or observe the relevant flow and ask the author to explain it. Keep main runnable; revert a broken feature only through an agreed corrective change.

On October 21 freeze new features. Use one recorded commit for the final demonstration and submission. Everyone rehearses their module and the overall flow. Member 1 coordinates release; Member 2 verifies user instructions; Member 3 verifies data/privacy tests; Member 4 verifies media and backup recording. Ammar reports no explicit prohibition on AI, provided members understand and can explain the project. Use the shared understanding checks; follow any later teacher instructions. The report submission format is PDF.

## Current starting point — October 16

See [TEAM_START.md](TEAM_START.md) for unassigned ownership, concrete first tasks and integration gates. The desktop preview now exists. Network/server/media folders contain starter guides only. Launch explicitly with `python run.py --demo`. The existing UI lives in client/ui/; temporary local data lives in client/demo/.
