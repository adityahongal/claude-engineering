# Tool Use

The point where the API stops being request-and-reply and becomes a loop. Claude cannot run
anything — it replies saying *which* function it wants called and with *which* arguments,
and your code decides whether to run it and what to send back. Every mechanism in this
folder exists to carry that exchange.

## Notes

**The shape of one tool call**

```
you:      messages + tool schemas
   ↓
Claude:   stop_reason="tool_use", content=[ tool_use block ]     ← a request, not an action
   ↓
you:      run the real function yourself
   ↓
you:      append Claude's reply UNCHANGED, then a tool_result block
   ↓
Claude:   the actual answer  (or another tool_use, and round again)
```

Two things follow from that, and most tool-use bugs are one of them:

- **Claude's tool_use reply must go back into `messages` verbatim.** A `tool_result` refers
  to a `tool_use_id`; drop the block that defined that id and the result points at nothing.
- **`tool_result` blocks are sent under the `user` role.** The role means "not the model",
  not "typed by a person".

The rest is the loop: keep going while `stop_reason == "tool_use"`, stop when it isn't.

**Why `chat()` returns a response here**

In the previous folder `chat()` returned `str`, because the reply was always text. That
would be actively wrong here — the interesting block is `tool_use`, and joining the text
blocks throws it away. So `tool-use/helpers.py` keeps the same names with a different
contract:

| | prompt-engineering | tool-use |
|---|---|---|
| `chat(...)` | `-> str` | `-> Message` |
| reading it | use the string | `text_from()`, `tool_uses()`, `wants_tool()` |

That is also why the file is copied rather than imported: one name cannot mean two things
across folders. Two copies is tolerable; if a third module needs this plumbing, that is the
signal to stop copying and build a real package.

**The tool registry**

`tools.py` holds each function, the schema describing it, and the `TOOL_FUNCTIONS` dict that
turns a name string into something callable. `run_tool(block)` ties them together and
always returns a `tool_result` — including on failure, flagged `is_error=True`, because
Claude is blocked waiting on that id and needs an answer either way.

## Gotchas

- **The block composition is not a contract — measured, not assumed.** The course describes
  a tool-use reply as `[text, tool_use]`. Two identical runs of
  `05_handling_message_blocks.py` on `claude-sonnet-5` returned `[thinking, tool_use]` and
  then `[tool_use]`. Never a text block, and not the same shape twice. Only `stop_reason`
  and the presence of a `tool_use` block can be relied on.
- **A `thinking` block has `.thinking`, not `.text`.** So `content[0].text` raises
  `AttributeError` when a thinking block comes first, and silently reads the wrong block
  when it doesn't. Filter by `.type`; never index.
- **`tool_uses()` returns a list.** Claude can ask for several tools in one reply, and
  `content[0]` quietly runs one and drops the rest.
- **Loop on `stop_reason`, not on the text.** Reading the reply for hints about whether it
  wants a tool is the usual wrong turn.
- **`tool_result.content` must be a string.** A dict or an int is a 400. `str()` for a
  string-returning tool, `json.dumps()` for anything structured.
- **Every `tool_use` block needs its own `tool_result`, in the same user message.** Reply to
  one of two and the turn is rejected — hence a list comprehension over `tool_uses()`
  rather than handling a single block.
- **The follow-up call must still pass `tools=`.** No new call is expected, but the history
  now refers to a tool and the definition has to travel with it to resolve.
- **A tool that raises still has to answer.** Claude is blocked on that `tool_use_id`;
  letting the exception escape leaves a request nothing ever replied to. Catch it, send
  `is_error=True` with the message, and Claude can retry with better arguments — which is
  the one place a bare `except Exception` is right rather than sloppy.
- **The schema description is not documentation.** It is the only thing Claude has when
  deciding whether to call the tool and what to pass — a vague description is a prompt
  engineering bug wearing a JSON hat.
- **A tool loop multiplies cost.** Every turn resends the entire history, tool results
  included, so a four-step loop is not four cheap calls — it is four increasingly expensive
  ones. Watch the tracker.
- **Guard against a runaway loop.** Nothing stops Claude asking for tools indefinitely.
  Cap the number of iterations.
- **The web search tool runs server-side** — no local function, no `tool_result`, and it is
  billed on top of tokens.

## Files

- `helpers.py` — client setup, message builders, `chat()` returning the response, block readers
- `tools.py` — the tool registry: functions, their schemas, and `run_tool()` dispatch
- `01_introducing_tool_use.py` — what tool use is, and what Claude does not do
- `02_project_overview.py` — the reminder project, and why it needs a loop
- `03_tool_functions.py` — the plain Python functions behind the tools
- `04_tool_schemas.py` — describing those functions to Claude
- `05_handling_message_blocks.py` — reading `tool_use` out of `response.content`
- `06_sending_tool_results.py` — running the function and returning a `tool_result`
- `07_multi_turn_with_tools.py` — keeping the history intact across a tool call
- `08_implementing_multiple_turns.py` — the loop
- `09_using_multiple_tools.py` — several tools, routing by name
- `10_fine_grained_tool_calling.py` — closer control over how tool calls are produced
- `11_text_edit_tool.py` — an Anthropic-defined tool, implemented locally
- `12_web_search_tool.py` — a server-side tool

Lesson files are numbered so the folder reads in course order. The two unnumbered modules
are shared code, and they have to be: **a module name cannot start with a digit**, so
`from 03_tool_functions import ...` is a `SyntaxError`. A numbered file can be run but never
imported, which means anything more than one lesson needs lives in `helpers.py` or
`tools.py`.

That constraint pushed the project toward the shape it wanted anyway. `tools.py` keeps each
function beside the schema that describes it and the dispatch that calls it — and since
nothing checks that a schema still matches its function, sitting in one file is the only
guard there is.

The course closes the module with a quiz, which produces no file.

## Run

```bash
cd 03-building-with-claude-api/tool-use
python 03_tool_functions.py      # no API call
python 06_sending_tool_results.py
```

The virtual environment and `.env` are shared — see the [module README](../README.md#setup).
