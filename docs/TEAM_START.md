# Team tasks and kickoff call

Assignments confirmed October 17, 2026. These replace the previous four-package ownership split. Names were assigned without assuming differences in skill.

## Current status

The live-integration branch implements real server/client authentication, presence, private/group messages, history, file transfer, discovery, recording and call paths. The old local demo source has been retired. Local TCP and offscreen GUI checks verify the core paths; hardware/multiple-device checks are still required. Read the root README for launch instructions and INTEGRATION_CONTRACT.md for actual operations. Historical kickoff tasks below explain ownership; they no longer indicate empty placeholder modules.

## Ammar — application and integration

Own client/ui/, client/network/, shared/, server/storage/, accounts/authentication, UDP discovery and live audio/video. Define the minimal shared framing/messages with the team first. Supply a terminal client harness and authenticated-session/storage boundaries; integrate their results into the GUI through queued Qt signals. All required media features remain in scope. Start microphone/camera feasibility immediately; avoid spending the remaining days on cosmetic polish.

## Abdullah — connections and presence

Branch: feature/connections. Work: server/transport/; coordinate shared helpers with Ammar.

First: start a TCP listener on a configurable address/port, accept two terminal clients, give each a worker, maintain a synchronized connection registry, and remove disconnected clients. Return/announce the active authenticated app users once Ammar supplies authentication. Agree serialized writes and bounded framing before routing messages.

Checks: two clients stay connected simultaneously; closing one removes it while the other remains usable; a broken/incomplete frame does not crash the server. Distinguish clean close from a connection failure that takes time to detect.

Deliver: run instructions, a working demonstration and explanation of bind/listen/accept, per-client sockets, threads, locks and cleanup. Do not build a separate UI, account system or message protocol.

## Ashna — private and group text

Branch: feature/messaging. Work: server/services/messaging.py and server/services/groups.py; coordinate transport with Abdullah and persistence with Ammar.

First: write routing functions using a small in-memory registry/harness, then attach them to the shared server. Route a private message only to its recipient; route group messages only to current members. Implement create/join/leave behaviour using Ammar's identity/storage service. Public/protected groups and persistent memberships remain required; do not invent a second database.

Checks: a third client cannot receive/read private text; nonmembers cannot send/read group text; an offline direct recipient produces an error. A success acknowledgement follows persistence, not merely socket send. Temporary in-memory experiments are not the final persistent feature.

Deliver: private and group terminal demonstrations, exact operations/events, successful and denied cases. Explain recipient lookup, group broadcast, membership and authenticated sender identity.

## Ayesha — file transfer

Branch: feature/file-transfer. Work: client/network/files.py and server/services/files.py; agree any transport changes with Abdullah and Ammar.

First: transfer a small synthetic text file with a separate TCP harness, declared size, bounded chunks and SHA-256 comparison. Then integrate client → server → authorized recipient/group through the agreed session-bound file channel. Do not send whole files as JSON/base64 or trust arbitrary destination paths.

Checks: reject files above 20 MiB; handle zero-byte files; interrupt halfway without publishing a corrupt complete file; reject checksum mismatch and unauthorized transfers. Write temporary files, verify before final rename, sanitize names, and close resources. File I/O/network work must stay off the GUI thread.

Deliver: sender/receiver instructions, verified file and interrupted-transfer demonstration. Explain byte streams, chunks, size accounting and why TCP alone does not replace application completion/integrity checks. Recorded voice can later reuse this path; microphone capture belongs to Ammar.

## Shared milestone

Two real clients authenticate, exchange private text, and retrieve authorized saved history through the existing UI. Then verify four physical clients, groups, attachments and required media. No one should wait until their entire package is finished before integrating.

## Kickoff call — about 40 minutes

Before: everyone installs Python 3.12/Git/editor, accepts collaborator access and opens the repo. Ammar opens the preview and this document.

1. 0–5 min: explain one server plus multiple clients on the same LAN. One laptop can run server and client together.
2. 5–10 min: demonstrate Home/private/groups. Say explicitly that messages are currently local; sample contacts are not live users.
3. 10–15 min: show run.py → client/ui/app.py → client/demo/service.py. Explain that the final path goes through sockets to server storage. Show where each person will add code.
4. 15–25 min: read each person's first task and checks together. Have them repeat their input, output and failure case in their own words.
5. 25–35 min: agree first text envelope/framing, terminal harness and integration handoffs using INTEGRATION_CONTRACT.md. Record unresolved decisions there before independent wire implementations. Pick the demonstration OS and identify four laptops.
6. 35–40 min: each person creates their branch, states the first small deliverable and agrees a same-day check-in time. Confirm exact October 22 submission time.

Say: “We are building one application together. Start with one small networking behaviour, use the shared protocol, demonstrate it in a terminal, and then we will connect it to the desktop UI. AI is allowed, but you must explain your code.”

After: review first experiments together and integrate incrementally. Each person writes their own feature explanation/report notes and rehearses the overall client-server flow.
