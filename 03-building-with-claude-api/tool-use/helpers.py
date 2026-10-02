"""Shared plumbing for the tool use lessons.

Mostly the same as the prompt-engineering helpers — client setup, message builders, the
error-handling chain — with one deliberate difference that matters:

    prompt-engineering:  chat(...) -> str          the reply text
    tool-use:            chat(...) -> Message      the whole response object

That is not tidying. A tool-use reply is a LIST of content blocks, and the interesting one
is a `tool_use` block, not text. Returning `"".join(text blocks)` would throw away the only
part worth reading. Every lesson in this folder inspects `response.content` directly, so
the response has to survive the trip out of chat().

This file is a copy rather than an import because of that signature change — the same
function name cannot mean two different things across folders. If a third module needs this
plumbing, that is the point to stop copying and make a real package.
"""

import os
import sys
from pathlib import Path

import anthropic
from anthropic.types import Message
from dotenv import load_dotenv

# Reuse the tracker rather than keeping a third copy of it. Same one-line path insert as the
# prompt-engineering helpers.
sys.path.insert(0, str(Path(__file__).parent.parent / "prompt-evaluation"))
from usage_tracker import UsageTracker  # noqa: E402  (import must follow the path insert)

# The loop at the bottom needs the dispatch. tools.py imports nothing from here, so this
# cannot go circular.
from tools import run_tools  # noqa: E402

MODEL = "claude-sonnet-5"
MAX_TOKENS = 8192
MAX_TURNS = 10


# ── setup ────────────────────────────────────────────────────────────────────────────

def get_client() -> anthropic.Anthropic:
    """Load .env, check the key is there, hand back a client.

    Order matters: the client reads ANTHROPIC_API_KEY once, at construction. Build it
    before load_dotenv() has run and it captures nothing.
    """
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    return anthropic.Anthropic()


def run(main_fn) -> None:
    """Call main_fn() with the standard error handling wrapped around it.

    Passed without parentheses — `run(main)`, not `run(main())`. With parentheses Python
    calls main first and hands over its return value, so the error handling would wrap
    nothing.
    """
    try:
        main_fn()
    except (KeyboardInterrupt, EOFError):
        print()
    except anthropic.AuthenticationError:
        sys.exit("Invalid API key.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited. Wait and retry.")
    except anthropic.APIStatusError as err:
        sys.exit(f"API error {err.status_code}: {err.message}")
    except anthropic.APIConnectionError:
        sys.exit("Network error. Check your connection.")


# ── messages ─────────────────────────────────────────────────────────────────────────

# The API is stateless, so the conversation is a list you own and resend in full every
# time. In tool use that list grows fast: one question can become user -> assistant
# (tool_use) -> user (tool_result) -> assistant, and all of it has to be sent back.

# Both builders accept three shapes: a string, a list of blocks, or a whole Message. The
# Message case is what lets the tool loop write `add_assistant_message(messages, response)`
# without remembering to reach for `.content` — forget it and the request fails, because a
# Message object is not a valid content value.

def _content_of(message):
    return message.content if isinstance(message, Message) else message


def add_user_message(messages: list, message) -> None:
    """A string for ordinary turns, or a LIST of blocks when returning tool results —
    tool_result blocks are sent under the "user" role, which reads oddly the first time.
    The role means "not the model", not "typed by a human".
    """
    messages.append({"role": "user", "content": _content_of(message)})


def add_assistant_message(messages: list, message) -> None:
    """A string, or Claude's reply verbatim — the Message itself or its `.content`. A
    request to call a tool has to go back into the history unchanged, or the tool_result
    that follows refers to nothing.
    """
    messages.append({"role": "assistant", "content": _content_of(message)})


# ── calling Claude ───────────────────────────────────────────────────────────────────

def chat(client: anthropic.Anthropic, messages: list, tools=anthropic.omit,
         model: str = MODEL, max_tokens: int = MAX_TOKENS, system=anthropic.omit,
         tracker: UsageTracker | None = None):
    """One request. Returns the WHOLE response, not just its text.

    anthropic.omit rather than None for the optional parameters — omit drops the field from
    the JSON body, None is sent as a literal null and rejected.
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        tools=tools,
        system=system,
    )

    if tracker is not None:
        tracker.record(response)

    return response


# ── reading a response ───────────────────────────────────────────────────────────────

def text_from(response) -> str:
    """Just the text blocks, joined. A response can hold text and tool_use together.

    Joined with "" where the course uses "\\n": consecutive text blocks are often one
    sentence split in pieces (citations do this), and a newline would break it apart.
    """
    return "".join(block.text for block in response.content if block.type == "text")


def tool_uses(response) -> list:
    """Every tool_use block in the response, in order.

    A list, not a single block — Claude can ask for several tools in one reply, and
    grabbing content[0] quietly runs one and drops the rest.
    """
    return [block for block in response.content if block.type == "tool_use"]


def wants_tool(response) -> bool:
    """True while Claude is still asking for tools.

    `stop_reason == "tool_use"` is the loop condition: keep going while it holds, stop
    when it doesn't. Checking the text for hints instead is the usual wrong turn.
    """
    return response.stop_reason == "tool_use"


# ── the tool loop ────────────────────────────────────────────────────────────────────

def run_conversation(client: anthropic.Anthropic, messages: list, tools: list,
                     tracker: UsageTracker | None = None, max_turns: int = MAX_TURNS,
                     on_turn=None, functions: dict | None = None):
    """Call Claude, run whatever tools it asks for, repeat until it stops asking.

    `messages` is extended in place, so the caller's list ends up holding the whole
    exchange. Returns the FINAL response — the course returns `messages`, but the caller
    already has that list, and the final response is what they actually want to read.

    on_turn(turn, response, results) is called after each turn, for anyone who wants to
    watch the loop work; results is None on the last turn.

    `functions` maps tool names to callables when they are not the tools.py registry.
    """
    for turn in range(1, max_turns + 1):
        response = chat(client, messages, tools=tools, tracker=tracker)
        add_assistant_message(messages, response)

        # The only exit that means "done". Not the text, not the block shapes.
        if not wants_tool(response):
            if on_turn:
                on_turn(turn, response, None)
            return response

        results = run_tools(response, functions)
        add_user_message(messages, results)
        if on_turn:
            on_turn(turn, response, results)

    # Not a return: the history now ends on a user tool_result, and handing back the last
    # response would pass off a tool request as an answer.
    raise RuntimeError(
        f"Claude was still asking for tools when the {max_turns}-turn cap ran out"
    )
