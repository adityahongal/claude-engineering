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

## Files

- `first_call.py` — reference version: `main()`, guard, block filtering, the full `except`
  chain. The shape to copy from.
- `making_a_request.py` — course follow-along, with the lesson notes kept inline and the
  original exploration commented above.

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
