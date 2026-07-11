# Claude Platform 101 — Notes

Course: [Claude Platform 101](https://anthropic.skilljar.com/claude-platform-101) · Status: 🟡 In progress

The developer on-ramp — learning to build with the Claude API (the Console, the
Workbench, and the structure of an API call).

> Note: I'm learning the API structure now and will **run the calls later** once I add
> credits (no free trial credit landed on my account). The concepts don't expire — code
> first, execute later.

## First API call

See [`hello-claude.mjs`](./hello-claude.mjs). Structure of a request:

- **`model`** — which Claude to use (`claude-haiku-4-5` = cheapest, for learning;
  `claude-opus-4-8` = smartest, pricier).
- **`max_tokens`** — cap on the reply length. Required.
- **`messages`** — the conversation. `role: "user"` is me; the reply comes back as the
  assistant.
- **`message.content[0].text`** — the response is an array of blocks; the text answer is
  in the first block.

## Key takeaways (from a frontend POV)

- **The API is just a POST request with a shape.** `model` + `max_tokens` + `messages`
  in, a structured response out. Same mental model as calling any REST API from the frontend.
- **The API key must stay server-side.** NEVER call Claude directly from browser/React —
  the key would be exposed in DevTools and anyone could spend on my account.
  Correct flow: `React frontend → my backend (Node) → Claude API`. The key lives on the backend.
- **The response is structured, not a plain string.** `content` is an array of blocks;
  text lives at `content[0].text`. Plan for that when wiring it into a UI.
- **The Workbench is the no-code way to feel the API** before writing code (draws from the
  same credit balance).

## Still to do

- [ ] Add credits and actually run `hello-claude.mjs`
- [ ] Try the same call in the Console Workbench
- [ ] Build a tiny `React → Node → Claude` flow once comfortable

## Questions I still have

- _(add anything unclear to revisit later)_
