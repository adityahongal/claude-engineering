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

**Filled in lesson by lesson.**

## Gotchas

- **`tool_uses()` returns a list.** Claude can ask for several tools in one reply, and
  `content[0]` quietly runs one and drops the rest.
- **Loop on `stop_reason`, not on the text.** Reading the reply for hints about whether it
  wants a tool is the usual wrong turn.
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
- `introducing_tool_use.py` — what tool use is, and what Claude does not do
- `project_overview.py` — what the module builds
- `tool_functions.py` — the plain Python functions behind the tools
- `tool_schemas.py` — describing those functions to Claude
- `handling_message_blocks.py` — reading `tool_use` out of `response.content`
- `sending_tool_results.py` — running the function and returning a `tool_result`
- `multi_turn_with_tools.py` — keeping the history intact across a tool call
- `implementing_multiple_turns.py` — the loop
- `using_multiple_tools.py` — several tools, routing by name
- `fine_grained_tool_calling.py` — closer control over how tool calls are produced
- `text_edit_tool.py` — an Anthropic-defined tool, implemented locally
- `web_search_tool.py` — a server-side tool

The course closes the module with a quiz, which produces no file.

## Run

```bash
cd 03-building-with-claude-api/tool-use
python tool_functions.py
```

The virtual environment and `.env` are shared — see the [module README](../README.md#setup).
