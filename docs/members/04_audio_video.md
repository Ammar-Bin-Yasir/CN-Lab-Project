# Member 4: Voice Messages and Calls

Read ../FINAL_PLAN.md and ../INTEGRATION_CONTRACT.md first. This is a proposed role guide; assign this role to one of Ammar, Abdullah, Ashna, or Ayesha at kickoff.

## Ownership

client/media/ and call service integration with Members 1/2; media test evidence. Coordinate edits outside these areas.

## Work sequence

1. Verify microphone/speaker/camera capture and playback on the target OS immediately; work with the networking owner on blockers.
2. Build a minimal two-device audio/video path with agreed formats before polishing controls.
3. Implement voice recordings with duration/cancel/send; reuse Member 3’s attachment service.
4. Implement per-call state, signaling, audio capture/playback, mute and reliable stop/cleanup.
5. Capture/compress camera frames with OpenCV and pass received frames to the Qt UI through the agreed events.
6. Test two independent call pairs, busy users, reject/timeout/disconnect, and continued text messaging; record backup demo media.

## Definition of done

Two-way intelligible audio, two-way live video with audio, repeated calls, missing hardware, one call ending without harming another, and bounded queues/resource cleanup. Keep a reproducible result and commit reference. Demonstrate through real integration, not only standalone mocks.

## Learning and presentation

Explain recorded files versus live streams, audio/video frame formats, buffering, TCP delay tradeoffs, and call IDs. Present calling flow and measured limitations.

## Daily handoff

Post completed behavior, branch/PR, tests, blocker, and the exact interface needed from another member. Add screenshots/log summaries using synthetic data, update report notes, and review one teammate’s change. Use ../AI_TASK_TEMPLATE.md for one small task at a time. Do not ask AI to generate the entire project.
