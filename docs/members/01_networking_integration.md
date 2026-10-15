# Role 1 — Networking and Integration (unassigned)

Read ../FINAL_PLAN.md and ../INTEGRATION_CONTRACT.md first. This is a proposed role guide; assign this role to one of Ammar, Abdullah, Ashna, or Ayesha at kickoff.

## Ownership

server/transport/, client/network/, shared/, discovery, release coordination. Coordinate edits outside these areas.

## Work sequence

1. Establish the repository skeleton and minimal shared framing/request contract with the team.
2. Implement two-client framed text; expand to authenticated four-client presence and service dispatch.
3. Expose a client adapter to the UI and bind file/media channels to authenticated sessions.
4. Implement UDP server discovery and manual fallback integration.
5. Pair with Member 4 on two-device media by October 16; coordinate daily end-to-end integration.
6. Coordinate packaging, demo setup, and the final tested commit.

## Definition of done

Fragmented/combined frames, four simultaneous clients, orderly/abrupt disconnects, channel authorization, and text remaining responsive during transfers/two calls. Keep a reproducible result and commit reference. Demonstrate through real integration, not only standalone mocks.

## Learning and presentation

Explain TCP stream framing, connection lifecycle, threads/locks, discovery versus chat, and the whole architecture. Present the architecture and coordinate the live demo.

## Daily handoff

Post completed behavior, branch/PR, tests, blocker, and the exact interface needed from another member. Add screenshots/log summaries using synthetic data, update report notes, and review one teammate’s change. Use ../AI_TASK_TEMPLATE.md for one small task at a time. Do not ask AI to generate the entire project.
