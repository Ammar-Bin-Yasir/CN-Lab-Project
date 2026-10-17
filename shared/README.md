# shared

**Owner package:** 1 coordinates; all affected owners review. Named owner: unassigned.

**Status:** Placeholder work area; no implementation yet.

## Responsibility

Wire constants/types and shared validation, with no GUI or database imports.

## First step

Freeze a minimal text contract together before writing protocol helpers. Document example messages, caps, errors and IDs in docs/INTEGRATION_CONTRACT.md. Do not infer a wire protocol from the demo adapter.

## Completion evidence

Put relevant checks in `tests/network/`. Demonstrate one successful flow and one meaningful failure, document commands/results and explain the mechanism. Use the repository's docs/TEAM_START.md and assigned member guide for the full task.

Do not place runtime data, credentials or personal recordings in this folder.
