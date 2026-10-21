# Team workflow

1. Follow the root readme to install Python 3.12 and client dependencies. Create virtual environments separately on each operating system.
2. Pull the final main branch before rehearsing. Run one server and the clients on a reachable LAN.
3. For any later fix, create a feature branch, change only the relevant modules, and preserve the shared protocol and authorization rules.
4. Keep tests, screenshots and temporary experiments outside Git. Never commit runtime databases, tokens, recordings or personal files.
5. Verify a successful scenario and a meaningful failure. Record the interpreter, commands and results honestly. Local muted audio transport is not proof of audible quality between laptops.
6. Review the diff with the responsible member before merging. Do not force-push or overwrite teammates' changes.

Roles and viva reading order are in TEAM_START.md; actual operations are in INTEGRATION_CONTRACT.md. For AI assistance, use AI_TASK_TEMPLATE.md and explain the resulting code yourself.
