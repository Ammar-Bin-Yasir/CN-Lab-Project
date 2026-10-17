# server/services

**Owner package:** 3 · Data; call signaling coordinated with 1 and 4. Named owner: unassigned.

**Status:** Placeholder work area; no implementation yet.

## Responsibility

Account, membership, authorized message/history and file-service operations.

## First step

Start with identity and group membership; do not implement fake file transfers. Use the authenticated session for access checks, never a user ID supplied as proof by a client.

## Completion evidence

Put relevant checks in `tests/storage/`. Demonstrate one successful flow and one meaningful failure, document commands/results and explain the mechanism. Use the repository's docs/TEAM_START.md and assigned member guide for the full task.

Do not place runtime data, credentials or personal recordings in this folder.
