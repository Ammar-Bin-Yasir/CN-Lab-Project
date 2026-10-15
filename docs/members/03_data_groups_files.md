# Member 3: Profiles, Persistence, Groups and Files

Read ../FINAL_PLAN.md and ../INTEGRATION_CONTRACT.md first. This is a proposed role guide; assign this role to one of Ammar, Abdullah, Ashna, or Ayesha at kickoff.

## Ownership

server/storage/, server/services/ for users/messages/groups/files; shared contracts coordinated. Coordinate edits outside these areas.

## Work sequence

1. Implement schema and one database worker; define IDs, username normalization, and parameterized queries.
2. Implement profile registration/login verification and authorized private/group history services.
3. Implement create/join/leave with persistent memberships and hashed shared group passwords.
4. Save text before acknowledgement; test server restart and unauthorized history requests.
5. Implement file metadata, safe storage, bounded chunk transfers, checksum verification, and access checks with Member 1.
6. Expose the same file-transfer path for Member 4’s recordings; document schema and test results.

## Definition of done

Wrong login, duplicate username, wrong group password, rejoin behavior, nonmember/outsider access denial, restart persistence, checksum match and interrupted transfers. Keep a reproducible result and commit reference. Demonstrate through real integration, not only standalone mocks.

## Learning and presentation

Explain persistence versus RAM, IDs versus names, password hashes, authorization, transactions, and binary file transfer. Present data model, group access, and sharing.

## Daily handoff

Post completed behavior, branch/PR, tests, blocker, and the exact interface needed from another member. Add screenshots/log summaries using synthetic data, update report notes, and review one teammate’s change. Use ../AI_TASK_TEMPLATE.md for one small task at a time. Do not ask AI to generate the entire project.
