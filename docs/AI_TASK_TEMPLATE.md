# Reusable AI Task Prompt

Copy the following into your coding assistant and fill the brackets. Ensure the assistant can read the repository files; attach the instructions if it cannot.

---
You are assisting our Computer Networks university project. Read AGENTS.md, docs/FINAL_PLAN.md, docs/INTEGRATION_CONTRACT.md, docs/TEAM_WORKFLOW.md, and my section in docs/TEAM_START.md. Follow the agreed stack, scope, and interfaces.

My role: [member/role].
My task: [one concrete behavior].
Allowed files/modules: [paths].
Existing dependencies/interfaces: [names and current status].
Acceptance checks: [successful flow and meaningful failure flow].

First inspect the code and briefly explain the flow and planned change. Implement a small complete solution. Do not introduce unrelated features, dependencies, or architecture changes. If a shared contract is missing, identify the exact decision needed. Keep useful independent work moving.

Verify the behavior and report what was actually tested. Explain the important socket/thread/database/UI choices and trace one example through the changed code. Finish with limitations and two understanding questions for me. Do not claim completion for placeholders or mocked-only flows.
---

Before accepting the result, ask yourself: Can I explain it? Did I see it work? Did I test failure? Does it match the shared protocol? Did I update my report/contribution notes?
