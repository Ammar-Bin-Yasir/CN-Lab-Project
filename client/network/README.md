# client/network

**Owner package:** 1 · Networking. Named owner: unassigned.

**Status:** Placeholder work area; no implementation yet.

## Responsibility

Background client adapter, connection lifecycle and discovery.

## First step

Agree the first text protocol in shared/ and docs/INTEGRATION_CONTRACT.md. Start with a CLI transport harness before connecting the GUI. Emit results/errors to Qt through queued signals; never recv on the UI thread.

## Completion evidence

Put relevant checks in `tests/network/`. Demonstrate one successful flow and one meaningful failure, document commands/results and explain the mechanism. Use the repository's docs/TEAM_START.md and assigned member guide for the full task.

Do not place runtime data, credentials or personal recordings in this folder.
