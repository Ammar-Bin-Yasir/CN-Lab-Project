# client/demo

**Owner package:** 2 coordinates preview changes. Named owner: unassigned.

**Status:** Existing preview code.

## Responsibility

Temporary sample contacts and local-only SQLite adapter in service.py.

## First step

Used by the --demo preview only. Do not use these profiles or this schema as the authoritative server implementation. Keep demo-only imports out of the eventual server.

## Completion evidence

Put relevant checks in `tests/test_preview.py`. Demonstrate one successful flow and one meaningful failure, document commands/results and explain the mechanism. Use the repository's docs/TEAM_START.md and assigned member guide for the full task.

Do not place runtime data, credentials or personal recordings in this folder.
