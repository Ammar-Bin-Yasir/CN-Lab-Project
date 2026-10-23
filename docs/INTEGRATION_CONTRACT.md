# Chatters integration contract

## Control channel

The shared/protocol.py control format is: four-byte big-endian length, UTF-8 JSON object, maximum body 65,536 bytes. Requests require version=1, type, request_id (1–64 characters), and object payload. Responses echo type/request_id and contain ok plus payload or error {code,message}. Unsolicited events have version,type,payload. The following schemas describe the current implementation.

| Operation | Payload | Result |
|---|---|---|
| register | username, display_name, password | profile {id,username,display_name}, token, file_port, media_port; signs in |
| login | username,password | same authentication result |
| profile_get | optional user_id integer; omitted means current account | full public profile |
| profile_update | display_name, bio, color, avatar | updated current-account profile |
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

Call sessions: separate TCP media port (default 5052). Initial framed {token,call_id,transport:"udp-v1"}; only an authenticated active participant may bind once per call. Response {ok:true,payload:{transport:"udp-v1",udp_port,identity,key,sample_rate:16000,blocksize:320}}. Identity is 16 random bytes and key is 32 random bytes, encoded as hex. Credentials exist only for this call session. Both TCP and UDP bind the same media port number, including when the server chooses an ephemeral port. TCP remains open for lifetime/teardown, with no media bytes after the handshake. An old TCP-media client/server is incompatible; update all participants together.

Live UDP packet format: network byte order `!4s16sBIIIHH`, followed by payload and a 16-byte truncated HMAC-SHA256 of direction-label+header+payload (label is the byte C for client-to-server or S for server-to-client; the label is not transmitted). Header: magic CHU1, endpoint identity, kind, per-datagram counter, per-stream frame/block sequence, sender monotonic timestamp in milliseconds modulo 2^32, fragment index, fragment count. Maximum total datagram 1,200 bytes, leaving 1,147 payload bytes. Kind 0 is registration/heartbeat with empty payload; kind 1 is exactly 640 audio bytes with index 0/count 1; kind 2 is JPEG fragments, at most 96 KiB per frame. Audio: mono signed int16, 16 kHz, 320 samples/20 ms. Video: target 320×240, 10 fps/quality 50. Only video calls may relay JPEGs. No RTP compatibility or media retransmission is provided.

The first signed heartbeat registers the UDP source address; its IP must match the authenticated TCP peer. Subsequent packets must use that exact endpoint. Signatures and a 256-packet replay window reject tampering/duplicates/very old packets while permitting reordering. The server re-signs forwarded packets with the recipient's session credentials; identities cannot route outside the authorized pair. UDP replies confirm registration (retry every 500 ms for up to five seconds); ongoing heartbeats run once a second. A registered media path idle for ten seconds is lost; a call without both registered endpoints times out after twenty seconds. Ringing still expires after thirty seconds. End/disconnect invalidates both participants' media credentials and frees only that call's reservations.

Client audio playout waits 60 ms, orders by block sequence, substitutes silence for missing blocks, rejects late blocks and resets on a large gap. Video reassembly keeps at most three incomplete frames, discards incomplete frames after 350 ms, and never displays a completed frame older than the last displayed/expired frame. Send queues are bounded and trim capture backlog. The relay limits each authenticated sender to 512,000 datagram bytes/second with a 128,000-byte burst budget; overload drops packets. These are LAN bounds, not adaptive congestion control. Device/network failures terminate the call visibly. Recorded voice and attachments retain the TCP file protocol above.

Packet signatures do not encrypt media. Because session credentials are exchanged over plaintext TCP, they do not defend against interception of the handshake. No transport-security claim is made.

Storage: accounts, rooms, memberships, messages and attachments share one SQLite-owning worker and transactions. Existing account-store API remains; operation() submits conversation/attachment work to that worker. Session-token and call state are memory-only, never persisted/logged. Server data directory must be retained for persistent accounts/history and attachments.

Verified outside Git: account checks, four real TCP clients, auth/session isolation, private/group history denial, wrong group password, restart history, binary file round-trip including zero-byte, size/checksum/interrupted-transfer failures, unrelated-user attachment denial, two simultaneous call pairs with synthetic audio/video packets and independent teardown, UDP discovery, fragmented/coalesced/oversized frames; two offscreen real Qt clients register/send/receive/navigate/sign out. These checks do not prove real hardware quality or a four-device LAN demonstration. Physical microphone/camera and target OS/package checks must be recorded separately.


### Additional local device evidence

The pinned dependencies installed successfully into .venv-live after a transient package-host DNS failure. Local PortAudio duplex capture/playback opened, a short WAV recorded/played, OpenCV encoded/decoded JPEG and captured a camera frame. Two actual audio workers exchanged blocks through the relay (muted silence to avoid feedback), and the actual camera worker sent three JPEG frames with concurrent audio. Qt file upload/download, incoming voice-call acceptance, mute and end-call cleanup also passed. No audio/images from the device checks were retained. Audible call quality and video calls across separate laptops are still unverified. Source runs are tested; no standalone executable or four-physical-device package has been validated.


### Offline private text
Private text accepts registered recipients regardless of presence. Storage validates the recipient and commits before acknowledgement. Online recipients receive the normal live event; offline recipients retrieve recent history after login through snapshot conversations and history. No delivery/read receipt, automatic replay or unlimited-history synchronization is added. The existing latest-50/48,000-byte history limit applies. Private file uploads and live calls still require online recipients.

### Public profiles

Both profile operations require authentication. A full profile contains id, username, display_name, bio, color, avatar and avatar_version. Profile updates always use the authenticated account ID, ignoring client-supplied identity. Send all editable fields: missing bio/avatar default to empty and color to #5865f2. Display names contain 1–64 characters, bios at most 280, and banner colors use six hexadecimal digits. Usernames cannot be edited. A successful update broadcasts refresh with profile_id; clients update current chat presentation without discarding the composer draft.

Profile pictures are center-cropped and resized by the desktop to 96×96 RGB PNG. Input images are limited to 5 MiB and 4096 pixels per dimension. The server accepts an empty avatar to remove it, or Base64 PNG bounded to 44,000 encoded characters / 32,768 decoded bytes; it validates structure, checksum, dimensions and bounded decompression. avatar_version is a truncated SHA-256 content digest. Snapshots and member lists add only color and avatar_version; clients fetch pictures on demand and retain at most 128 profile cache entries. This keeps picture bytes out of presence snapshots.

A profiles table is created additively in the existing SQLite database. Names remain in users; profile details share the same worker and update transaction. Existing accounts, memberships, messages and files are retained. Both server and clients need this version for profile requests.
