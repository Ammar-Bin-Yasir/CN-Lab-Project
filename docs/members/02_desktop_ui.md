# Member 2: Desktop UI and Experience

Read ../FINAL_PLAN.md and ../INTEGRATION_CONTRACT.md first. This is a proposed role guide; assign this role to one of Ammar, Abdullah, Ashna, or Ayesha at kickoff.

## Ownership

client/ui/, QSS, assets/, screenshots and user guide. Coordinate edits outside these areas.

## Work sequence

1. Sketch login, Home, private, and group screens; implement the three-region shell using Qt layouts.
2. Use synthetic view data briefly while the adapter is pending; clearly label it and replace it with real events.
3. Connect register/login, presence, conversation selection, history, and composer to Member 1’s adapter.
4. Add create/browse/join/leave dialogs with public/protected access, attachments, and recording controls.
5. Integrate Member 4’s incoming/active call UI; check empty/loading/error/disconnected states.
6. Verify keyboard navigation, resizing, scrolling, unread indicators, consistent spacing and actual-device launch.

## Definition of done

Home/group context switching, wrong-password feedback, no lost history on navigation, responsive typing during network work, and readable layout on the demo screen. Keep a reproducible result and commit reference. Demonstrate through real integration, not only standalone mocks.

## Learning and presentation

Explain Qt events/signals, main-thread UI ownership, navigation states, and how user actions reach the network. Present UI/UX and write the user guide.

## Daily handoff

Post completed behavior, branch/PR, tests, blocker, and the exact interface needed from another member. Add screenshots/log summaries using synthetic data, update report notes, and review one teammate’s change. Use ../AI_TASK_TEMPLATE.md for one small task at a time. Do not ask AI to generate the entire project.
