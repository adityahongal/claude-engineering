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
- **The course's loop slide files Claude's reply under the wrong role.** It shows
  `add_user_message(messages, response)` right after `chat()`; that has to be
  `add_assistant_message`. The written summary has it right.
- **Guard against a runaway loop.** Nothing stops Claude asking for tools indefinitely.
  `run_conversation` caps the turns and **raises** past the cap rather than returning —
  the last response is a tool request, and returning it would pass it off as an answer.
- **Don't `json.dumps` a string result.** The course dumps every tool output, which wraps a
  string in quotes (`'"2026-10-01"'`). `run_tool` passes strings through and only dumps
  structured output.
- **Independent tool calls arrive together — measured.** "30, 60 and 90 days from today"
  came back as one reply with three `tool_use` blocks, all answered in one user message.
  The dependent call (today's date) still took its own turn first.
- **Adding a tool is four edits that nothing cross-checks.** Function, schema, `ALL_SCHEMAS`,
  `TOOL_FUNCTIONS` — miss one and it fails only when Claude calls that tool.
  `check_registry()` catches every one of those before the first API call.
- **A tool description is guidance, not a constraint — measured.** `set_reminder` says to use
  `add_duration_to_datetime` for anything relative. For "a week from this Thursday" Claude
  called `add_duration_to_datetime` with `duration: 0` purely to learn today's weekday,
  then added the 7 days itself. Right answer, wrong path; for a +7 it got away with it.
- **Claude fills gaps you didn't ask it to.** "177 days after Jan 1st, 2050" names no time;
  Claude set the reminder for 09:00 on its own and only mentioned it after the fact. A tool
  that acts on the world should probably ask, or say what it assumed.
- **Fine-grained tool calling moved out of beta and onto the tool — course drift.** The
  course passes `fine_grained=True`, which sends the beta header
  `fine-grained-tool-streaming-2025-05-14`. Now it is `"eager_input_streaming": True` on each
  tool definition, with the ordinary `client.messages.stream(...)` and no header. The
  `input_json` events are unchanged.
- **Buffering is real, and large — measured.** The same request, streamed both ways: buffered
  went 5.17s with nothing, then the whole input in a burst (0 of 1,854 chars by halfway).
  Eager never went quiet for more than 0.18s (879 of 1,715 chars by halfway).
- **`snapshot` is not a progress bar.** The SDK parses it in jiter's partial mode, which drops
  an unfinished string until its closing quote — so a streaming abstract is invisible in
  `snapshot` even with eager streaming on — and keeps a half-arrived number as a smaller,
  wrong one (`"word_count": 1` while `12` arrives). Live progress means accumulating
  `partial_json` yourself.
- **Eager streaming moves validation to you.** The API stops validating the input, and the
  SDK's tolerant parser returns a truncated object rather than raising. Check
  `stop_reason == "max_tokens"` first, validate against the schema before running anything,
  and catch `ValueError` around the stream for JSON it cannot parse at all.
- **Don't ask Claude for a number your code can compute.** `meta.word_count` was wrong on
  three of four runs (161 words reported as 169, 171 as 178, 174 as 172). Count it yourself.
- **The text editor's version, name and commands all changed — course drift.** The course's
  `text_editor_20250124` / `str_replace_editor` is now `text_editor_20250728` /
  `str_replace_based_edit_tool`. The name is what arrives in `block.name`, so dispatch keyed
  on the old one matches nothing. `undo_edit` is gone: four commands remain (`view`,
  `create`, `str_replace`, `insert`), and undo is yours to build from backups.
- **The text editor's `path` is untrusted model output.** Claude decides where your code
  writes. Resolve the path first (collapsing `..` and symlinks), then check it is inside the
  sandbox — a string-prefix check on the raw path is not enough.
- **Claude verifies its own edits — measured.** Asked for two changes, it viewed the folder,
  viewed the file, made both in one `str_replace`, then viewed the file again before
  answering. Five calls for a two-line job; the re-check is turn 4.
- **The web search version changed, and the new one drops citations — measured.** The course's
  `web_search_20250305` is now `web_search_20260209` on Sonnet 5, which filters results in
  server-side code first (results come back as an encrypted `code_execution_tool_result`).
  Same question on both: the old version returned 4 citations; the new one split its text
  where citations go and returned empty lists. Inline citations need the old version.
  Tokens did not clearly favour the new one either: 25,013 old vs 22,256 and 34,691 new,
  one question each — noisy, but no saving to bank on for a small query.
- **The web search tool runs server-side** — no local function, no `tool_result`, no 08
  loop; one call holds the query, results and answer. The early stop is `pause_turn`: resend
  the conversation unchanged, no "continue" message. A failed search does not raise — its
  `content` is an error object instead of a list. Billed per search on top of tokens, and
  the results count as input tokens.
- **`allowed_domains` includes subdomains.** `python.org` also admitted `test.python.org`, the
  staging site.

## Files

- `helpers.py` — client setup, message builders (string, block list, or a whole `Message`),
  `chat()` returning the response, block readers, and `run_conversation()` — the capped loop,
  which takes a `functions` map for tools outside the registry
- `tools.py` — the tool registry: `get_current_datetime`, `add_duration_to_datetime`,
  `set_reminder`, their schemas, `run_tool()` / `run_tools()` dispatch, and `check_registry()`
- `01_introducing_tool_use.py` — what tool use is, and what Claude does not do
- `02_project_overview.py` — the reminder project, and why it needs a loop
- `03_tool_functions.py` — the plain Python functions behind the tools
- `04_tool_schemas.py` — describing those functions to Claude
- `05_handling_message_blocks.py` — reading `tool_use` out of `response.content`
- `06_sending_tool_results.py` — running the function and returning a `tool_result`
- `07_multi_turn_with_tools.py` — a question that needs two tools in sequence, walked turn
  by turn without a loop
- `08_implementing_multiple_turns.py` — the loop: a chain, parallel calls, and the cap
- `09_using_multiple_tools.py` — the third tool, the full reminder chain, and checking the
  side effect really happened
- `10_fine_grained_tool_calling.py` — buffered vs eager tool-input streaming, timed side by
  side, and validating an input nobody else checked
- `11_text_edit_tool.py` — the Anthropic-defined text editor, implemented in a sandbox
  behind a path guard, with a behaviour check on Claude's edit
- `12_web_search_tool.py` — the server-side search tool, both versions side by side:
  sources, inline citations, and what each costs

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
