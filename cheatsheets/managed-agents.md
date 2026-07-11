# Managed Agents — Cheatsheet

**What it is:** Anthropic runs the whole agent loop AND hosts a container where the agent's
tools execute. You just *define* the agent — you don't write the loop yourself.

**Managed agent vs plain agent loop:**
- Plain agent loop → *you* drive the loop in code (call → tool → call…). Full control, more plumbing.
- Managed agent → *Anthropic* drives it. Less code, less control. The "hosted/serverless" version.

**The four primitives:**
- **Agent** — the config: model, system prompt, tools. Reusable, versioned.
- **Session** — one run. References an agent + environment.
- **Environment** — the sandbox template for the container.
- **Container** — where the tools actually execute.

**The one rule:** create the **Agent once** (save its ID) → create a **Session every run**.
model/system/tools live on the Agent, NEVER on the Session.

**Event stream flow:**
1. Open the stream (`sessions.events.stream`)
2. Send the kickoff (`user.message`) — **stream-first, then kickoff**, or you miss early events
3. Consume events until done

**Idle-break gate:** don't stop on `session.status_idle` alone — sessions go idle transiently
(e.g. waiting on you for a tool approval). Stop on `terminated`, or `idle` with a terminal
stop_reason (anything except `requires_action`).

**Start with a stub:** build the bare skeleton first (default toolset, simple prompt, trivial
task), prove the plumbing runs end-to-end, THEN add real tools/MCP/logic.

**Frontend analogy:** managed agents are the serverless version — you declare the function,
the platform runs it. Stub-first = stubbing a component before wiring real data in.
