# Claude Engineering

Notes and working code for building on the Claude API — picking a model, the agent loop,
tool use, MCP, context management, and RAG.

Each folder has the notes for one area plus code you can actually run. `cheatsheets/` has
the short version of each topic, for when you just need to remember how something works.
The notes lean on frontend analogies (props, state, the event loop) wherever the
comparison actually holds up.

## Coverage

| Area | Reference | Status |
|---|---|---|
| Claude fundamentals — prompts, context, LLM basics | [`01-claude-101/`](./01-claude-101/) | Documented |
| Platform — models, agent loop, tools, skills, MCP, managed agents | [`02-platform-101/`](./02-platform-101/) | Documented |
| Claude Code — the terminal coding agent | [`claude-code-101/`](./claude-code-101/) | Documented |
| Building with the Claude API — prompt engineering, tool use, RAG | [`03-building-with-claude-api/`](./03-building-with-claude-api/) | In progress |
| Claude on Amazon Bedrock | — | Planned |
| Claude on Google Cloud Vertex AI | — | Planned |
| Model Context Protocol — introduction and advanced topics | — | Planned |

## Repository layout

- `NN-topic-name/` — notes, gotchas, and example code for one area
- `cheatsheets/` — one page per topic, condensed
- Anything secret goes in a `.env` file, and those are git-ignored everywhere

## Certifications

Anthropic Academy — Claude 101, Claude Code 101, Claude Platform 101.
