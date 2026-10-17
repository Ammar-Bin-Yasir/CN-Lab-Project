# Team workflow

Ownership and first tasks are in TEAM_START.md. All three teammates focus on networking; Ammar owns UI and integration, storage, discovery and live media. Everyone must understand their code and contribute their report section and viva explanation.

1. Install Python 3.12, Git and an editor; accept repository access. Run the preview using the root README.
2. Start from the agreed foundation after PR #1 is merged. Before that, inspect feature/desktop-preview; do not commit directly to another person's branch.
3. Create your own branch: feature/connections (Abdullah), feature/messaging (Ashna), feature/file-transfer (Ayesha).
4. Agree relevant message formats with Ammar before implementing communication. Use one framing helper; do not generate separate incompatible protocols.
5. Implement the first small task and run a terminal experiment, then integrate daily. Temporary nicknames in an experiment are not production authentication.
6. Commit only your task's files. Push your branch and open a PR to main. Include behaviour, how to run, success/failure results, limitations and any interface changes.
7. Explain the flow to Ammar, get review, then merge after verification. Do not merge or force-push another person's work.
8. Pull updated main before the next task. Record your contribution and report evidence locally; no credentials, personal media or runtime data in Git.

AI prompt: use AI_TASK_TEMPLATE.md. Ask for one behaviour, not the entire project. Review every generated line; each member must explain a successful flow and a failure case. Local checks are still mandatory even though test files are not kept in Git.

Daily check-in: what works, demonstration, blocker, interface needed and next task. Ammar coordinates shared files and supports the harder file/media work. Report remains PDF; target OS and exact submission time still need confirmation.
