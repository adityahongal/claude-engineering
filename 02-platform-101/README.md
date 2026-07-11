 Course: [Claude Platform 101](https://anthropic.skilljar.com/claude-platform-101) · Status:
  🟡 In progress

  The developer on-ramp — learning to build with the Claude API: models, the agent loop,
  tools, skills, MCP, and context management.


  ## Model tiers & use cases                 
  - Haiku (fastest/cheapest) → Sonnet (balanced) → Opus (most capable Opus-tier) → Fable (most
  capable overall) → Mythos (restricted access).
  - Compared tiers side by side on latency + token counts. Pick the smallest tier that does
  the job.

  ## The agent loop
  - Claude runs in a loop: respond → if it wants a tool, run it and feed the result back →
  repeat until `stop_reason: "end_turn"`.
  - The code drives the loop; Claude decides what to do each turn. Did a minimal working
  example.

  ## Tool use
  - Tools are JSON schemas with 3 parts: `name`, `description`, `input_schema`.
  - Claude uses the `description` to decide when to call a tool. Can pick among multiple
  tools.
  - Tool runner = SDK helper that drives the tool-call loop automatically.

  ## Extended thinking
  - Claude can reason step-by-step (chain of thought). Adaptive thinking (Opus 4.7+): Claude
  decides when/how much to think.

  ## Built-in tools
  - Server tools (Anthropic runs them, no agent loop needed by me): web search, code
  execution, web fetch.
  - Client tools (I execute them): memory, bash.

  ## Skills
  - Task-specific instructions + files Claude loads only when relevant (progressive
  disclosure).                               
  - Skills = know-how; Tools = actions. Flow: load into context → upload → attach → run.

  ## MCP (Model Context Protocol)
  - Open standard for connecting Claude to external tools/data.
  - Tools vs Skills vs MCP: actions / know-how / standardized connection (the "USB standard").
  - Connector = a pre-built integration built on MCP (a "USB device" already made). MCP = the
  standard.

  ## Context management
  - "Pay on the way in, and on the way out" applies to ALL LLMs — billed per input token AND
  per output token.
  - API is stateless — I resend full conversation each call, so context + cost grow every
  turn.
  - Four patterns + compaction (summarize), prompt caching (reuse stable prefix), memory tool
  (persist across sessions).

  ## Key takeaways (frontend POV)            
  - The agent loop is just an event loop: call → check state → handle side effects → call
  again.
  - Tools are typed contracts — a JSON schema is basically a function signature (like typing
  props).
  - Stateless API = I own the state, like the frontend re-sending state each render.

  ## Questions I still have
  - Advanced MCP topics — pending (separate course).