# Instructions for AI Coding Assistants

## Purpose and authority

Help the Chatters team (Ammar, Abdullah, Ashna, Ayesha), a four-person BSCS team implement and understand its October 22 Computer Networks project. Read docs/FINAL_PLAN.md, docs/INTEGRATION_CONTRACT.md, docs/TEAM_WORKFLOW.md, and the assigned member guide before editing. If these files are alongside this file in the planning packet, use those local paths. The final plan supersedes earlier discussion drafts. Respect explicit later human decisions; update documentation when the team changes the plan.

## Scope

Build Python desktop clients with PySide6 Qt Widgets/QSS and a threaded Python socket server on a LAN. Use SQLite, UDP server discovery with manual fallback, username/password profiles, public/protected groups, saved authorized history, private/group messaging, file/media sharing, recorded voice, and independent one-to-one audio/video calls. One call per user; test two pairs. Follow the specified Home/private/group navigation. No extra website, framework, database service, AI chat feature, admin system, or unrequested dependency. TLS is excluded from this submission commitment; do not claim transport security.

## Before changes

Identify the assigned issue, owner, acceptance criteria, dependencies, and affected files. Inspect the actual repository; do not assume planned code exists. Explain the intended behavior and message flow briefly. If a contract is unresolved, identify the exact gap and coordinate its resolution before generating incompatible code. Do useful independent work while waiting for necessary information.

## Implementation

Make the smallest complete, readable change for one task. Prefer explicit functions and clear responsibilities. Use existing shared helpers. Avoid speculative abstractions, giant rewrites, unnecessary dependencies, and placeholder implementations presented as complete. Do not change other modules' contracts or overwrite another member's work without coordination.

Keep GUI changes on its main thread; use queued signals from workers. Use framed messages, bounded buffers, timeouts, synchronized writes, safe shutdown, and protected shared state. Do not hold global locks across blocking I/O. Keep SQLite connection ownership in the database worker; use parameterized SQL and transactions. Verify authorization using the authenticated session for every conversation, group, attachment, and call operation. Hash user/group passwords with salts; never log secrets. Keep received filenames within managed storage, enforce sizes, and verify hashes before marking completion.

## Understanding and verification

Explain non-obvious networking/concurrency logic, not every basic Python statement. For each task, show a successful scenario and a meaningful failure scenario. Run relevant checks where available; report commands/results honestly and distinguish passed, failed, and not run. Never invent test evidence, measured latency, screenshots, or completed features. Preserve reproducible bug details and fix causes rather than hiding errors.

End with: changed files and behavior; tests/evidence; remaining limitations; and two short questions the member should be able to answer about the change. The human must trace an example and understand the important choices before merging. Follow the course's AI-use rules and attribution requirements when supplied.

## Git and privacy

Work in the assigned feature branch and allowed paths. Do not push, merge, rewrite shared history, or delete teammates' changes without authorization. Never commit real credentials, runtime databases, recordings, private reference screenshots, or session tokens. Use synthetic fixtures. Do not install or upgrade dependencies unrelated to the task. Never store user passwords as plaintext or treat a nickname as authentication.

## Confirmed team facts

Repository: https://github.com/Ammar-Bin-Yasir/CN-Lab-Project. Roles remain unassigned; do not infer them from names or guide numbers. Final report format is PDF. Ammar reports AI is permitted provided each member understands and can explain the project; support that learning rather than hiding generated logic. Classmates may join the demonstration after the four-client baseline is tested. Exact submission time, presentation duration, and target operating systems remain unknown.
