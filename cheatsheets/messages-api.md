# Messages API — Cheatsheet

**The one idea:** the API is stateless. Every call is a blank slate, so the conversation
is a list *you* maintain and resend in full each time.

## The minimal call

```python
import anthropic
from dotenv import load_dotenv

load_dotenv()                      # .env → environment, BEFORE the client is built
client = anthropic.Anthropic()     # reads ANTHROPIC_API_KEY at construction, once

response = client.messages.create(
    model="claude-sonnet-5",       # exact string from the docs
    max_tokens=1024,               # a ceiling, not a target
    messages=[{"role": "user", "content": "Hello"}],
)
```

Those three parameters are required on every request.

## Reading the response

```
response.content  →  [block, block, ...]  →  keep type == "text"  →  join
```

```python
"".join(b.text for b in response.content if b.type == "text")
```

`content` is a **list of blocks**, not a string. A block's `.type` is `text`, `tool_use`,
or `thinking` — and only text blocks have `.text`. `content[0].text` works until the day
it doesn't.

## Conversation = a list you own

```python
messages = []
messages.append({"role": "user", "content": "..."})       # your turn
# → send the WHOLE list
messages.append({"role": "assistant", "content": reply})  # Claude's turn, appended by you
```

Only two roles exist: `user` and `assistant`. Forget the assistant append and the bot
answers every message as if it were the first. Turn 10 resends turns 1–9 — context and
cost grow with every message.

## System prompt

```python
client.messages.create(..., system="You are a patient math tutor.")
```

**Top-level parameter, not a message role.** (OpenAI puts `system` in the list; Anthropic
doesn't.) Constant per session, but re-sent on every call like everything else.

Optional arguments default to `anthropic.omit`, never `None` — `None` is sent as JSON
`null`, `omit` leaves the key out entirely.

## Streaming

```python
with client.messages.stream(model=..., max_tokens=..., messages=messages) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)     # both arguments are required
    return stream.get_final_text()
```

Context manager (holds a connection). `text_stream` is a generator. `flush=True` or Python
buffers stdout and prints everything at once — looking exactly like no streaming.

## Structured output

```python
class Rule(BaseModel):
    source: list[str]

response = client.messages.parse(..., output_format=Rule)
rule = response.parsed_output           # a validated Rule, not a string
```

The schema goes with the request, so the wrong shape can't be generated. Replaces the old
prefill + `stop_sequences` trick.

## Errors — catch specific before general

```
APIConnectionError      never reached the server (network, DNS, timeout)
APIStatusError          the server answered with an error status
├── BadRequestError         400   ← includes "credit balance is too low"
├── AuthenticationError     401   ← bad key
├── RateLimitError          429
└── InternalServerError     5xx
```

`APIStatusError` is the parent — it goes **last**, or it swallows its subclasses. A
`TypeError` is not an API error at all: that's the SDK refusing before any request.

## Removed since the course was recorded

| Was taught | Status now | Instead |
|---|---|---|
| `temperature` / `top_p` / `top_k` | Gone from SDK 1.0.0; 400 on current models | Prompting; `extra_body` + Haiku to demo |
| Assistant prefill + `stop_sequences` | 400 on Sonnet 5 / Opus 5 / 4.6–4.8 | `output_format` + Pydantic |
| `thinking` with `budget_tokens` | Replaced | Adaptive thinking + `effort` |

Check the installed SDK, not the video.

## Frontend analogy

`anthropic.Anthropic()` is a preconfigured axios instance — base URL and auth header set
once, reused. The stateless message list is the same reason a component re-receives all
its props on every render: nothing is remembered for you, so you hold the state and pass
it in each time.
