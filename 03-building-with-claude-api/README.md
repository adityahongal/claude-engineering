# Building with the Claude API

Prompt engineering, tool use, embeddings, and RAG — the part where you actually build
things on top of Claude. Examples here are in Python. The SDK looks the same in every
language, but Python is what the rest of the GenAI ecosystem (LangChain, FastAPI,
Pydantic) is built on, so that's the one worth having in your fingers.

Source: Anthropic Academy — [Building with the Claude API](https://anthropic.skilljar.com/)

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env      # then put your key in .env
python first_call.py
```

`.env` is git-ignored. The key has to stay server-side — see
[`../cheatsheets/api-key-security.md`](../cheatsheets/api-key-security.md).

## Files

| File | What it covers |
|---|---|
| `first_call.py` | Building the client, `messages.create`, reading content blocks, handling errors |

Prompt engineering, tool use, embeddings, and RAG each get their own module alongside
this one.

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

## Caveats

- **The API is stateless.** Every call resends the whole conversation, so context *and*
  cost grow with each turn. Nothing carries over unless you send it again.
- **You pay on the way in and on the way out** — input tokens and output tokens are
  billed separately.
- **Model IDs are exact strings.** `claude-haiku-4-5` is already complete; tacking a date
  on the end gets you a 404.
- **Running these live needs API credits.** The code can be written and reviewed without
  them — add credits when you want real responses back.
