# Building with the Claude API

Prompt engineering, tool use, embeddings, and RAG — the part where you actually build
things on top of Claude. Examples here are in Python. The SDK looks the same in every
language, but Python is what the rest of the GenAI ecosystem (LangChain, FastAPI,
Pydantic) is built on, so that's the one worth having in your fingers.

Source: Anthropic Academy — [Building with the Claude API](https://anthropic.skilljar.com/)

## Setup

The virtual environment and `requirements.txt` live at the **repo root**, shared by every
Python module here — so this is a one-time setup, not per-folder.

From the repo root:

```bash
python3 -m venv .venv             # once, ever
source .venv/bin/activate         # every new terminal session
pip install -r requirements.txt   # once, or when deps change
```

Then, in this folder:

```bash
cp .env.example .env              # then put your key in .env
python api-access/first_call.py
```

One `.env` covers the whole module — `load_dotenv()` searches the current directory and
walks up, so scripts in the sub-folders find it without their own copy.

`source .venv/bin/activate` only applies to the terminal tab you run it in — open a new
tab and you'll need it again. Your prompt shows `(.venv)` when it's active; `deactivate`
exits. `.venv/` is git-ignored and disposable — delete it and rebuild from
`requirements.txt` any time.

`.env` is git-ignored too. The key has to stay server-side — see
[`../cheatsheets/api-key-security.md`](../cheatsheets/api-key-security.md).

## Layout

One folder per course module, filled in as each is worked through.

| Folder | Covers |
|---|---|
| `api-access/` | Keys, requests, multi-turn, system prompts, streaming, structured data |
| `prompt-evaluation/` | Eval workflow, test datasets, model-based and code-based grading |
| `prompt-engineering/` | Clear and direct, specificity, XML tags, examples |
| `tool-use/` | Tool functions and schemas, message blocks, multi-turn tool loops |
| `rag/` | Chunking, embeddings, the RAG flow, BM25, multi-index retrieval |
| `claude-features/` | Extended thinking, images, PDFs, citations, prompt caching |
| `mcp/` | MCP clients and servers, tools, resources, prompts |
| `agents-workflows/` | Parallelization, chaining, routing, agents vs workflows |

`.env.example` is the key template — copy it to `.env`, which is never committed.
Claude Code is covered separately in [`../claude-code-101/`](../claude-code-101/).

Each folder carries its own `README.md` with the notes and gotchas for that module.

## Notes

### The request shape

A Claude API call is just an HTTP POST. The key goes in a header, the prompt goes in the
JSON body. The SDK builds that request for you, but underneath it's the same shape you'd
write by hand:

```
httpx.post(url, headers={"x-api-key": ...}, json={"model": ..., "messages": [...]})
```

Three fields are required every time: `model`, `max_tokens`, and `messages`.

### The response is a list of blocks, not a string

This is the first thing that trips you up. `response.content` is a list, and every item
in it has a `type`. A plain answer is one `text` block — but that same list can also hold
`tool_use` blocks (Claude asking you to run a tool) or `thinking` blocks. So filter by
`type` instead of grabbing `content[0]`, because the first block isn't always text.

### `max_tokens` is a ceiling, not a target

It caps how much Claude can generate in one response. Hit the cap and the answer just
stops mid-sentence, with `stop_reason` set to `max_tokens`. The examples here keep it
small on purpose to keep costs predictable.

### Credentials

`anthropic.Anthropic()` picks up `ANTHROPIC_API_KEY` from the environment on its own.
`load_dotenv()` reads `.env` into the environment first, so the key never has to appear
anywhere in the code.

## Frontend mental model

- **The SDK is axios, not `fetch`.** `anthropic.Anthropic()` wraps the same HTTP call you
  could write by hand — it just handles auth headers, retries, and parsing so you don't
  have to. Same tradeoff as reaching for axios over raw `fetch`.
- **Reading `content` is like rendering `children`.** You don't assume `children` is a
  single string and render it blindly; you check what each child actually is first. Same
  here — walk the list, check each block's `type`, handle the ones you care about.
- **A stateless API means you own the state.** Every call resends the full conversation,
  the same way a component re-receives all its props on every render. Nothing persists on
  the server between calls, so the `messages` list is your state — if you don't send it,
  it didn't happen.
- **The key needs a backend, for the same reason `.env` doesn't protect a React app.**
  Anything shipped to the browser is readable in DevTools. The call has to originate from
  a server you control.

## Caveats

- **The API is stateless.** Every call resends the whole conversation, so context *and*
  cost grow with each turn. Nothing carries over unless you send it again.
- **You pay on the way in and on the way out** — input tokens and output tokens are
  billed separately.
- **Model IDs are exact strings.** `claude-haiku-4-5` is already complete; tacking a date
  on the end gets you a 404.
- **Running these live needs API credits.** The code can be written and reviewed without
  them — add credits when you want real responses back.
