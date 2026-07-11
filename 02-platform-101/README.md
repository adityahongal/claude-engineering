# Claude Platform 101 — Notes

Course: [Claude Platform 101](https://anthropic.skilljar.com/claude-platform-101) · Status: ✅ Done

The developer on-ramp — learning to build with the Claude API: models, the agent loop,
tools, skills, MCP, context management, and managed agents.

## Model tiers & use cases
- Haiku (fastest/cheapest) → Sonnet (balanced) → Opus (most capable Opus-tier) → Fable (most capable overall) → Mythos (restricted access).
- Compared tiers side by side on latency + token counts. Pick the smallest tier that does the job.

## The agent loop
- Claude runs in a loop: respond → if it wants a tool, run it and feed the result back → repeat until `stop_reason: "end_turn"`.
- The code drives the loop; Claude decides what to do each turn. Did a minimal working example.

## Tool use
- Tools are JSON schemas with 3 parts: `name`, `description`, `input_schema`.
- Claude uses the `description` to decide when to call a tool. Can pick among multiple tools.
- Tool runner = SDK helper that drives the tool-call loop automatically.

## Extended thinking
- Claude can reason step-by-step (chain of thought). Adaptive thinking (Opus 4.7+): Claude decides when/how much to think.

## Built-in tools
- Server tools (Anthropic runs them, no agent loop needed by me): web search, code execution, web fetch.
- Client tools (I execute them): memory, bash.

## Skills
- Task-specific instructions + files Claude loads only when relevant (progressive disclosure).
- Skills = know-how; Tools = actions. Flow: load into context → upload → attach → run.

## MCP (Model Context Protocol)
- Open standard for connecting Claude to external tools/data.
- Tools vs Skills vs MCP: actions / know-how / standardized connection (the "USB standard").
- Connector = a pre-built integration built on MCP (a "USB device" already made). MCP = the standard.

## Context management
- "Pay on the way in, and on the way out" applies to ALL LLMs — billed per input token AND per output token.
- API is stateless — I resend full conversation each call, so context + cost grow every turn.
- Four patterns + compaction (summarize), prompt caching (reuse stable prefix), memory tool (persist across sessions).

## Managed Agents
- A managed agent = Anthropic runs the agent loop AND hosts a container where tools execute. I just *define* the agent; I don't write the loop.
- **Managed agents vs the agent loop:** plain agent loop = I drive the loop in code; managed agents = Anthropic drives it. Less plumbing, less control.
- **The four primitives:** Agent (config: model/system/tools) · Session (one run) · Environment (the sandbox template) · Container (where tools actually run).
- **Mandatory flow:** create the Agent ONCE (save its ID) → create a Session every run. model/system/tools live on the Agent, never the Session.
- **Event stream:** a session streams events (agent messages, tool use, status). **Stream-first, then kickoff** — open the stream before sending the first `user.message`, or I miss early events.
- **Idle-break gate:** don't stop on `session.status_idle` alone (it goes idle transiently). Stop on `terminated`, or `idle` with a terminal stop_reason (not `requires_action`).
- **Start with a stub:** build the bare skeleton agent first (default toolset, simple prompt, trivial task), confirm the wiring runs end-to-end, THEN add real tools/MCP/logic.
- **Also learned:** outcomes (state what "done" looks like), multi-agent coordination, working in parallel.
- See [`first-agent.mjs`](./first-agent.mjs) — the stub agent (not yet run, needs credits).

## Key takeaways (frontend POV)
- The agent loop is just an event loop: call → check state → handle side effects → call again.
- Tools are typed contracts — a JSON schema is basically a function signature (like typing props).
- Stateless API = I own the state, like the frontend re-sending state each render.
- Managed agents = the "hosted/serverless" version: Anthropic runs the loop + container, I just declare the agent.
- Stub-first = same as stubbing a component before wiring real data — prove the plumbing, then build up.

## Questions I still have
- Advanced MCP topics — pending (separate course).
