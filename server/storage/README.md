# server/storage

**Owner package:** 3 · Data. Named owner: unassigned.

**Status:** Placeholder work area; no implementation yet.

## Responsibility

Server schema, database worker, transactions and persistence.

## First step

Design stable IDs and constraints; one worker owns the SQLite connection. Tests use temporary databases. The client/demo schema is disposable, not authoritative.

## Completion evidence

Put relevant checks in `tests/storage/`. Demonstrate one successful flow and one meaningful failure, document commands/results and explain the mechanism. Use the repository's docs/TEAM_START.md and assigned member guide for the full task.

Do not place runtime data, credentials or personal recordings in this folder.
