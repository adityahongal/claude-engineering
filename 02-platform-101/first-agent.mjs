// first-agent.mjs — my first Managed Agent (a "stub" agent)
// STATUS: written & understood, NOT YET RUN (needs credits; managed agents cost more).
//
// A "stub" = the bare skeleton: minimal agent, one trivial task. Goal is to prove the
// four primitives connect and the event stream flows — THEN add real tools/logic.
//
// Run later with:
//   npm install @anthropic-ai/sdk
//   export ANTHROPIC_API_KEY="sk-ant-..."   (server-side only — never in browser)
//   node first-agent.mjs

import Anthropic from "@anthropic-ai/sdk";

const client = new Anthropic();

// ── SETUP (run ONCE, then save these IDs and reuse them) ──────────────────
// Environment = the sandbox container the agent's tools run in.
const environment = await client.beta.environments.create({
  name: "my-first-env",
  config: { type: "cloud", networking: { type: "unrestricted" } },
});

// Agent = the config. model / system / tools live HERE, never on the session.
const agent = await client.beta.agents.create({
  name: "My First Agent",
  model: "claude-haiku-4-5",                     // cheapest tier — swap for claude-opus-5 when quality matters
  system: "You are a helpful assistant.",
  tools: [{ type: "agent_toolset_20260401" }],   // built-in bash/read/write/search/etc.
});
// → In real code: store agent.id + environment.id; stop recreating them every run.

// ── RUNTIME (every run) ───────────────────────────────────────────────────
// Session = one run. It just points at the agent + environment.
const session = await client.beta.sessions.create({
  agent: agent.id,
  environment_id: environment.id,
});

// STREAM-FIRST, THEN KICKOFF: open the stream before sending the first message,
// or the earliest events get missed.
const stream = await client.beta.sessions.events.stream(session.id);

await client.beta.sessions.events.send(session.id, {
  events: [
    { type: "user.message", content: [{ type: "text", text: "Say hello in one sentence." }] },
  ],
});

// Consume the stream until the run is truly done.
for await (const event of stream) {
  if (event.type === "agent.message") {
    for (const block of event.content) {
      if (block.type === "text") process.stdout.write(block.text);
    }
  }
  // Idle-break gate: don't stop on plain idle (it goes idle transiently).
  if (event.type === "session.status_terminated") break;
  if (event.type === "session.status_idle" && event.stop_reason?.type !== "requires_action") break;
}
