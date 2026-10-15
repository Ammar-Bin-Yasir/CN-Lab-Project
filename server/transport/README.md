# server/transport

**Owner package:** 1 · Networking. Named owner: unassigned.

**Status:** Placeholder work area; no implementation yet.

## Responsibility

TCP listener, framed reads/writes, connection cleanup, routing and later discovery.

## First step

Implement bounded framing first. Coordinate authenticated sessions and storage jobs with package 3. Every disconnect must clean up without stopping unrelated clients.

## Completion evidence

Put relevant checks in `tests/network/`. Demonstrate one successful flow and one meaningful failure, document commands/results and explain the mechanism. Use the repository's docs/TEAM_START.md and assigned member guide for the full task.

Do not place runtime data, credentials or personal recordings in this folder.
