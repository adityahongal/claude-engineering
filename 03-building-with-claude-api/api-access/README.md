# Accessing Claude with the API

Getting a key, building a client, sending a request, and reading what comes back — plus
failing usefully when any of that goes wrong.

## Notes

**The request**

Every call goes through `client.messages.create()` and needs three things:

| Parameter | What it is |
|---|---|
| `model` | Which Claude to use — an exact string from the docs |
| `max_tokens` | A ceiling on the response, **not** a target |
| `messages` | The conversation so far |

`max_tokens` is a safety limit. Claude writes what it thinks the answer needs and stops;
it doesn't try to fill the budget. If it *does* hit the cap the reply is cut off
mid-sentence and `stop_reason` comes back as `max_tokens`.

**Messages and roles**

`messages` is a list of dicts, each with a `role` and `content`:

- `"user"` — what you send
- `"assistant"` — what Claude has said

The API is stateless, so this list is the entire memory of the conversation. Nothing is
stored server-side between calls — whatever you don't resend, Claude never knew.

**Multi-turn conversations**

Because nothing is stored, a "conversation" is a list you maintain and resend in full:

```
messages = []
  append {"role": "user", ...}      →  send the WHOLE list  →  reply
  append {"role": "assistant", ...}
  append {"role": "user", ...}      →  send the WHOLE list  →  reply with context
```

Claude never remembers — it re-reads the transcript you hand it on every call. Turn 10
resends turns 1–9, so context and cost grow with every message. This is where the
"pay on the way in and on the way out" idea stops being abstract.

Appending the reply as a plain string is fine while responses are text-only. Appending
`response.content` (the block list) instead preserves structure, and becomes necessary
once tool use enters the picture.

Helpers that append to the list can return `None` and mutate in place — a list is passed
by reference, so the function is changing the caller's object, not a copy. Rebinding
(`messages = messages + [msg]`) looks equivalent and silently isn't.

**Turning it into a chat loop**

A chatbot is the same exchange wrapped in `while True:` — read input, append, send the
whole history, print, append the reply. One API call per turn; two means a leftover from
somewhere.

Give it a way out. `while True:` with no `break` can only be stopped with Ctrl+C, which
raises `KeyboardInterrupt` and exits through a traceback. A quit word plus
`except (KeyboardInterrupt, EOFError)` covers both the deliberate exit and Ctrl+D.

Where the `try` sits is a design decision: wrapping the whole loop means one transient
error ends the session, while catching inside the loop lets it recover and carry on.

**System prompts**

A system prompt shapes how Claude answers — tone, role, what it should and shouldn't do.
It's a plain string passed as a **top-level parameter** on `create()`:

```python
client.messages.create(
    model=MODEL, max_tokens=MAX_TOKENS,
    messages=messages,
    system=system_prompt,      # alongside messages, not inside it
)
```

It is **not** a role in the `messages` list. Anthropic has exactly two roles, `user` and
`assistant`. Most tutorials online are OpenAI-shaped, where `system` *is* a message role —
that difference is the usual source of confusion.

In a loop, define it once above the loop. It's constant for the session, but the API is
stateless, so it gets re-sent with every request just like the history does.

For an optional system prompt, default the parameter to `anthropic.omit` rather than
`None`. `None` is sent as a literal JSON `null`; `omit` leaves the key out of the request
entirely. Two different requests.

**Temperature — and why it no longer applies to Claude**

Temperature controls the sampling step: near `0` the highest-probability token is picked
almost every time; near `1` probability is spread wider and output varies. Low for
factual work and extraction, high for brainstorming and creative writing.

It is on its way out of this API on two fronts:

- **The Python SDK removed it.** In `anthropic` 1.0.0, `temperature`, `top_p` and `top_k`
  are gone from `messages.create()` — passing one raises `TypeError` locally, before any
  request. `extra_body={"temperature": ...}` still puts it in the JSON body.
- **Current models reject it.** `claude-sonnet-5`, `claude-opus-5` and the 4.7/4.8 family
  return a 400. `claude-haiku-4-5` still accepts it.

Steer current Claude models with prompting, or with `output_config.effort` where the
model supports it. The concept still matters everywhere else — OpenAI, Gemini and every
LangChain wrapper take a `temperature` argument.

Demonstrating it needs a **comparison, not a chat loop**: the same prompt run several
times at `0.0` and again at `1.0`. And each run needs a **fresh message list** — reuse one
and the earlier answers sit in the history, so Claude avoids repeating itself. That looks
like temperature working when it isn't.

**Response streaming**

`client.messages.stream(...)` replaces `create(...)` and is a **context manager**, so it
needs `with` — there's an HTTP connection held open for the duration, and the block
guarantees it closes even if something throws part-way through.

```python
with client.messages.stream(model=MODEL, max_tokens=MAX_TOKENS, messages=messages) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
    return stream.get_final_text()
```

`stream.text_stream` is a **generator**: each iteration yields the next chunk and pauses.
It's a convenience layer over the raw event types (`MessageStart`, `ContentBlockDelta`,
`MessageStop`, …), filtering them down to just the text deltas. Iterate the stream itself
if you need the raw events.

Both `print` arguments matter. `end=""` stops a newline after every chunk; `flush=True`
pushes each one to the terminal immediately — without it Python buffers stdout and the
whole response appears at once, which defeats the point.

`get_final_text()` returns the assembled string once the stream finishes, which is what
you append to the history. `get_final_message()` gives the whole `Message` instead, with
`stop_reason` and `usage`.

Streaming changes the structure of the code: output has to happen **as chunks arrive**, so
the function that streams is also the function that prints. Whatever called it must stop
printing the return value, or everything appears twice. Error handling is unaffected —
the request fires on entering the `with`, so failures surface through the same handlers.

**Reading the response**

```
response.content  →  [block, block, ...]  →  keep type == "text"  →  join
```

`response.content` is a **list of blocks**, not a string. Each block has a `.type`:
`"text"`, `"tool_use"` (Claude asking to run a tool), or `"thinking"`. Only text blocks
carry a `.text` attribute.

The course uses `content[0].text`, which works while every response is plain text. Filter
by type instead and the same line keeps working once tools and thinking arrive.

**Getting the key in**

```
.env file  →  load_dotenv()  →  process environment  →  Anthropic() reads it
```

`load_dotenv()` doesn't hand you the value — it copies `.env` into the process
environment, which is where the SDK looks. That indirection is the point: in production
there's no `.env`, the platform sets real environment variables, and the same code runs
untouched.

**Error handling**

The SDK's exceptions form a tree, and the shape tells you what to catch:

```
APIConnectionError      never reached the server (network, DNS, timeout)
APIStatusError          the server answered with an error status
├── BadRequestError         400
├── AuthenticationError     401
├── PermissionDeniedError   403
├── NotFoundError           404
├── RateLimitError          429
└── InternalServerError     5xx
```

`except` clauses are tested top to bottom, first match wins — so subclasses go above
`APIStatusError`, or the parent swallows them. Catch what you can act on differently
(bad key, rate limit, no network) and let `APIStatusError` be the catch-all that prints
whatever the server said.

## Frontend mental model

- **`anthropic.Anthropic()` is a preconfigured axios instance.** Base URL and auth header
  set once, reused for every call. Build one and keep it — it holds a connection pool.
- **The guard clause is `if (!user) return res.status(404)`.** Check the bad case first,
  bail out, and the happy path continues unindented.
- **`sys.exit(msg)` is `process.exit(1)`** — the same thing you wrote in `connectDB()`
  when Mongo wouldn't connect.
- **Reading `content` is like rendering `children`.** You don't assume it's one string and
  render blindly; you check what each item is first.

## Gotchas

- A `.py` file must `print()`. The REPL echoes every expression, so a bare
  `message.content[0].text` looks correct and produces **no output at all** when run.
- **Model IDs are exact strings** — copy them, never build one by analogy. `claude-sonnet-4-0`
  is valid, so `claude-sonnet-5-0` looks reasonable and 404s. It's `claude-sonnet-5`.
- **`anthropic` is the module, `Anthropic` is the class.** The exception types live on the
  module, so `Anthropic.AuthenticationError` raises `AttributeError` — and only at the
  moment an error occurs, which is when you least want a second failure.
- **The client reads the key once, at construction.** Build it before `load_dotenv()` and
  it captures `None` permanently; loading `.env` afterwards can't repair it.
- **A passing guard doesn't prove a working client.** The guard checks the environment; a
  client built earlier already took its own copy. The check passes while the client is
  broken.
- That failure raises a plain **`TypeError`**, not an `anthropic.*` error — so none of the
  handlers above catch it.
- **400 ≠ 401.** A 400 with a billing message means the key was accepted and only credits
  are missing. Auth failures are 401. Read the status before assuming the key is wrong.
- Anything at **module level runs on import**, not just on run. `if __name__ == "__main__":`
  guards only the `main()` call — not other top-level lines.
- **Forget to append the assistant reply and Claude gets amnesia.** No error, no warning —
  it just answers the follow-up as though it were the first question. A missing append is
  almost always the cause.
- **Iterate `response.content`, not the response.** The response is a Pydantic model, so
  looping over it yields `(field_name, value)` tuples and `block.type` raises
  `AttributeError`.
- **Mutate, don't rebind.** `messages.append(x)` changes the caller's list;
  `messages = messages + [x]` rebinds a local name and the caller sees nothing.
- **Watch out for `message` next to `messages`.** One letter apart, completely different
  things — the response versus the history. Name the response `response`.
- **Adapting a script into a loop leaves scaffolding behind.** A second `chat()` call that
  made sense as "turn 2" becomes a duplicate request on every iteration — double the cost,
  and its reply never reaches the history. Count the API calls per turn: it should be one.
- **`while True:` needs an exit.** Without a `break`, Ctrl+C raises `KeyboardInterrupt` and
  the program dies through a traceback. Catch it (and `EOFError` for Ctrl+D) to leave at
  exit code 0.
- **Comments go stale when code moves.** "Add the initial user question" stops being true
  the moment it's inside a loop. Re-read the comments after any restructure.
- **`system` is a top-level parameter, not a message role.** Only `user` and `assistant`
  exist in `messages`. OpenAI-shaped tutorials will tell you otherwise.
- **`system=None` is not the same as omitting it.** `None` goes on the wire as JSON `null`;
  `anthropic.omit` leaves the key out. A default only matters when a call actually falls
  through to it — which is why code that always passes a value never reveals the problem.
- **A `TypeError` from the SDK is not an API error.** `temperature` was removed from
  `messages.create()` in SDK 1.0.0, so it fails locally before any request. Switching
  models can't fix a parameter the client library no longer has.
- **`temperature=0` was never a guarantee of identical output**, on any model or provider.
  It makes sampling near-deterministic, not deterministic. Don't build retry logic that
  assumes otherwise.
- **Reusing one message list across comparison runs invalidates the comparison.** Prior
  answers in the history make Claude avoid repeating itself, which is easy to mistake for
  the parameter you're testing.
- **`flush=True` is not optional when streaming.** Python buffers stdout, so without it the
  chunks accumulate and print all at once at the end — looking exactly like no streaming.
- **`text_stream` is an instance attribute, not a class one.** Inspecting `MessageStream`
  won't show it; it's assigned in `__init__`.
- **Streaming moves printing into the streaming function**, so the caller must stop
  printing the return value or every response appears twice.

## Files

- `first_call.py` — reference version: `main()`, guard, block filtering, the full `except`
  chain. The shape to copy from.
- `making_a_request.py` — a single request: client setup, `messages.create`, block
  filtering, guard clause and the error chain.
- `multi_turn_conversations.py` — a two-turn conversation: `add_user_message` /
  `add_assistant_message` helpers maintaining the list, resent in full each call.
- `simple_chatbot.py` — the same exchange in a `while True:` loop, with a quit word and
  clean handling of Ctrl+C / Ctrl+D.
- `system_prompts.py` — the chat loop with a system prompt steering it, passed as a
  top-level parameter on every call.
- `streaming_response.py` — the chat loop with `messages.stream()`, printing chunks as
  they arrive and appending the assembled text to the history.
- `temperature_haiku_model_only.py` — one prompt run three times at `0.0` and three times
  at `1.0`. Uses `claude-haiku-4-5` and `extra_body`, since the SDK dropped the parameter
  and current models reject it — the deviation is explained in the file's docstring.

The helpers are duplicated across the last two files rather than shared. Each file stays
readable end to end, which matters more here than avoiding repetition.

## Run

```bash
source ../../.venv/bin/activate     # from this folder
cp ../.env.example ../.env          # once — then add your key
python making_a_request.py
```

One `.env` at the module root serves every sub-folder — `load_dotenv()` searches the
current directory and walks up.

Without credits the run ends with `API error 400: Your credit balance is too low...` and
exit code 1. That is the error handling working, not a setup problem.
