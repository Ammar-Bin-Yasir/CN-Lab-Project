# Chatters integration contract

## Control channel

The shared/protocol.py control format is: four-byte big-endian length, UTF-8 JSON object, maximum body 65,536 bytes. Requests require version=1, type, request_id (1–64 characters), and object payload. Responses echo type/request_id and contain ok plus payload or error {code,message}. Unsolicited events have version,type,payload. The following schemas describe the current implementation.

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


### Offline private text
Private text accepts registered recipients regardless of presence. Storage validates the recipient and commits before acknowledgement. Online recipients receive the normal live event; offline recipients retrieve recent history after login through snapshot conversations and history. No delivery/read receipt, automatic replay or unlimited-history synchronization is added. The existing latest-50/48,000-byte history limit applies. Private file uploads and live calls still require online recipients.
