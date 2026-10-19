# Shared Integration Contract

This is a proposed minimal contract to finalize together before independent implementation. Do not generate four incompatible protocols. Ammar coordinates changes and each affected owner updates producer and consumer together.

## Control channel

Proposed framing: 4-byte unsigned big-endian payload length followed by that many UTF-8 JSON bytes. Set a documented control-frame cap (proposed 64 KiB), loop until the entire frame is read, reject malformed/oversized payloads, and serialize writes. A frame is not necessarily one recv call.

Request envelope: version, type, request_id, payload. Response: version, type, request_id, ok, payload or a stable error code/message. Unsolicited events have type and payload. Use server-issued IDs and UTC timestamps, rendering local time in the client. The authenticated socket determines the sender; never accept an arbitrary sender identity from the request.

Agree on these operations: register, login, list_users, list_conversations, list_groups, create_group, join_group, leave_group, get_history, send_message, offer_transfer, accept/complete_transfer, request_call, accept/reject/end_call. Events include presence_changed, message_received, membership_changed, transfer_progress/result, call_incoming/state. Exact payloads and error codes must be written with one example each as their feature is implemented.

## Interfaces between owners

- UI requests actions through a client service/adapter; it does not use SQL or raw sockets. The adapter emits queued Qt events with IDs, results, and errors.
- Server handlers validate requests, call services, and route results; services do not import GUI modules.
- Storage owns SQLite access and transactions. Services receive results through the agreed database-job mechanism without holding global network locks while waiting.
- File service is shared by ordinary attachments and recorded audio. Agree on transfer ID, declared size/type, checksum, recipient/group target, and completion/error states.
- Media owner defines capture/playback and start/stop APIs; transport owner binds extra channels to sessions and calls; UI owner displays events and controls.

## Binary channels and session binding

File/audio/video frames use dedicated channels with bounded lengths and buffers. Before implementation, document the initial handshake: session-bound server-issued token, transfer/call ID, media type, and permitted direction. Validate membership/participant access at creation and use; never trust a call ID or claimed user ID alone. Bound short-lived token lifetime and avoid logging tokens.

Client/server agree on file chunk size, image encoding/resolution, audio sample rate/channels/format, and frame caps before media integration. These values must match at both ends. Do not invent incompatible formats in separate AI sessions.

## State decisions

- One active client session per account initially; reject a second login clearly. This is a proposed implementation default to confirm at kickoff.
- Group create automatically adds creator; join is idempotent; leave removes access. Disconnect does not remove persisted membership. No default group.
- A successful text-send acknowledgement means saved/accepted by server, not read by the recipient. Initially reject offline direct recipients clearly.
- Calls: requested → ringing → active → ended, with rejected/busy/timeout/failed exits. Reserve participant availability atomically, release on every terminal path, and identify every event by call ID.
- File: offered → accepted → transferring → verified/complete, with rejected/failed/cancelled exits. Write temporary files and expose final files only after verification. Do not execute received files.
- On disconnect, fail pending requests cleanly, stop affected workers, and retain saved data. Reconnect requires reauthentication; do not silently replay uncertain messages.

## Minimum contract tests

Fragmented/combined control frames; oversize rejection; simultaneous sends; invalid credentials; private-history denial; protected-group wrong password; file checksum and interrupted transfer; call busy race; one call ending while another continues. Test behavior rather than mocking away the boundaries being verified.

## Implemented account-storage boundary — October 19

Ammar's `server/storage/accounts.py` provides `AccountStore(path)`. It creates a server-owned users table; it does not import or migrate preview accounts. Stable integer IDs identify users. Usernames normalize with Unicode NFKC, whitespace stripping and lowercase, then require 3–32 ASCII letters/numbers/underscores. Display names allow up to 64 characters without control characters. Passwords require 8–128 characters and use independent 16-byte salts with scrypt.

```python
from server.storage import AccountStore

store = AccountStore('runtime/server.sqlite')
profile = store.register('ammar', 'Ammar', 'demonstration-password').result(timeout=5)
profile = store.authenticate('ammar', 'demonstration-password').result(timeout=5)
# profile: {'id': 1, 'username': 'ammar', 'display_name': 'Ammar'}
store.close()
```

These calls belong in server workers, never GUI handlers. Both methods return Futures; the sole storage worker owns its SQLite connection. Registration commits before returning success. Validation, duplicate usernames and incorrect credentials raise ValueError through the Future. A full pending queue raises queue.Full immediately; a closed store raises RuntimeError. A Future wait timeout does not cancel a possibly executing write: do not blindly retry registration. Database setup failures propagate from construction. close() drains accepted jobs and joins the worker; call it from the coordinating server thread, not a Future callback running on the database worker. Do not block while holding the connection-registry lock.

Abdullah's transport must use the returned ID as authenticated connection state, enforce the session policy and never accept a client-supplied sender ID as authentication. This storage component does not create tokens, reserve active sessions, rate-limit login or authorize messaging. Public profiles contain no hashes or salts. Mapping ValueError into stable wire error codes and agreeing login/register payloads remain integration work; the example above is a Python API, not a frozen network schema.

Local checks (outside Git) verified normalized duplicate rejection, incorrect/unknown credentials, invalid input, simultaneous duplicate registration, stable identity after restart, closed-store rejection and invalid database-path startup. No LAN or GUI authentication is claimed by those checks.


## Live implementation — integration branch

The previously proposed control framing is now implemented in shared/protocol.py: four-byte big-endian length, UTF-8 JSON object, maximum body 65,536 bytes. Requests require version=1, type, request_id (1–64 characters), and object payload. Responses echo type/request_id and contain ok plus payload or error {code,message}. Unsolicited events have version,type,payload. Payload schemas below are the implementation baseline, coordinated in this branch. No other teammate implementation was published when this work began.

| Operation | Payload | Result |
|---|---|---|
| register | username, display_name, password | profile {id,username,display_name}, token, file_port, media_port; signs in |
| login | username,password | same authentication result |
| ping | {} | {} |
| snapshot | {} | people public profiles, groups {id,name,protected,joined}, conversations target strings, online user IDs |
| create_group | name,password (empty means public) | target |
| join_group | target,password | target |
| leave_group | target | target |
| members | target | member public profiles |
| history | target | chronological recent message records |
| send_message | target,body | saved message record |
| request_call | recipient integer ID, mode voice/video | call record |
| accept_call/reject_call/end_call | call_id | call record |

Targets are user:<positive integer ID> or group:<positive integer ID>. Sender identity comes only from the authenticated connection. History returns the latest up to 50 messages within a 48,000-byte JSON budget. Message fields: id,sender_id,sender,body,created (UTC ISO timestamp),attachment (nullable ID); history also includes attachment_name. Private incoming events rewrite target to the sender conversation from the recipient's perspective.

Events: refresh (request a new snapshot), message_received (message), call_incoming (call plus caller_name), call_state (active call or ended record with reason). An acceptance means persisted, not read/delivered. Presence changes trigger refresh; user profiles and group metadata are discoverable to signed-in accounts, but histories/attachments are authorized separately. Control threads serialize writes and use socket timeouts; desktop workers exchange results through queued Qt signals. Pending requests time out without automatic replay.

File channel: separate TCP port. Initial framed JSON {op:upload,token,target,name,size,sha256} or {op:download,token,id}. The token must match a currently authenticated control connection. Upload response is framed {ok,payload:{id}}, followed by exactly size raw bytes, then framed completion metadata or error. Downloads return authorized metadata then exactly size bytes. 20 MiB maximum, 64 KiB chunks, SHA-256 checks, server-generated storage paths and temporary-file publication. Interrupted files are not exposed as complete. Membership is rechecked at upload completion and download initiation. Downloads cannot retract already authorized bytes after a user leaves.

Call channel: separate TCP port. Initial framed {token,call_id}; only active participants may bind once per call. Response contains audio settings. Then each media packet is four-byte big-endian packet length (including its type byte), followed by type byte and bytes. Maximum packet 262,144 bytes. Type 1: exactly 640 audio bytes, mono signed int16 at 16 kHz, 320 samples/20 ms. Type 2: JPEG video, target 320×240 at 10 fps/quality 50. Video is permitted only for video calls. Outgoing queues are bounded; stale packets drop rather than accumulate. Server relays each pair independently; teardown releases only that call's participants/channels. Ringing times out at 30 seconds; active calls without both media channels time out after 20 seconds. Device startup errors terminate the affected call visibly.

Storage: accounts, rooms, memberships, messages and attachments share one SQLite-owning worker and transactions. Existing account-store API remains; operation() submits conversation/attachment work to that worker. Session-token and call state are memory-only, never persisted/logged. Server data directory must be retained for persistent accounts/history and attachments.

Verified outside Git: account checks, four real TCP clients, auth/session isolation, private/group history denial, wrong group password, restart history, binary file round-trip including zero-byte, size/checksum/interrupted-transfer failures, unrelated-user attachment denial, two simultaneous call pairs with synthetic audio/video packets and independent teardown, UDP discovery, fragmented/coalesced/oversized frames; two offscreen real Qt clients register/send/receive/navigate/sign out. These checks do not prove real hardware quality or a four-device LAN demonstration. Physical microphone/camera and target OS/package checks must be recorded separately.


### Additional local device evidence

The pinned dependencies installed successfully into .venv-live after a transient package-host DNS failure. Local PortAudio duplex capture/playback opened, a short WAV recorded/played, OpenCV encoded/decoded JPEG and captured a camera frame. Two actual audio workers exchanged blocks through the relay (muted silence to avoid feedback), and the actual camera worker sent three JPEG frames with concurrent audio. Qt file upload/download, incoming voice-call acceptance, mute and end-call cleanup also passed. No audio/images from the device checks were retained. Audible call quality and video calls across separate laptops are still unverified. Source runs are tested; no standalone executable or four-physical-device package has been validated.
