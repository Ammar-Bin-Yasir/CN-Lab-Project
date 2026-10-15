# Shared Integration Contract

This is a proposed minimal contract to finalize together before independent implementation. Do not generate four incompatible protocols. Member 1 coordinates changes and each affected owner updates producer and consumer together.

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
