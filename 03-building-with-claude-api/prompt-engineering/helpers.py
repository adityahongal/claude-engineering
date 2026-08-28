"""Shared plumbing for the prompt engineering lessons.

Everything in this module was hand-written once per file across the previous two folders —
the message builders, the chat wrapper, the key check, the error-handling chain. None of it
is what this module is about, so it lives here once and gets imported.

Nothing here is magic. Every function takes what it needs as an argument and returns a
value; there is no hidden global state and no framework. Read it once before using it —
knowing what `chat()` actually does matters more than saving the typing.

Import from a lesson file in this folder:

    from helpers import get_client, add_user_message, chat, run
"""

import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# The usage tracker was written in the prompt-evaluation folder and there is no reason to
# copy it — a second copy would drift from the first. Python only imports from directories
# it knows about, so the sibling folder is added to the search path here.
#
# In a real project this is what packaging solves: you'd make the whole thing an installable
# package and import `from claude_course.usage_tracker import UsageTracker` from anywhere.
# For a folder of course exercises, two explicit lines are the honest trade.
sys.path.insert(0, str(Path(__file__).parent.parent / "prompt-evaluation"))
from usage_tracker import UsageTracker  # noqa: E402  (import must follow the path insert)

MODEL = "claude-sonnet-5"
MAX_TOKENS = 4096


# ── setup ────────────────────────────────────────────────────────────────────────────

def get_client() -> anthropic.Anthropic:
    """Load .env, check the key is actually there, and hand back a client.
    """
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    return anthropic.Anthropic()


def run(main_fn) -> None:
    """Call main_fn() with the standard error handling wrapped around it.

    `main_fn` is a function passed in as a value — note there are no parentheses at the
    call site (`run(main)`, not `run(main())`). With parentheses Python would call main
    first and pass its *return value*, which is not what's wanted; without them it passes
    the function itself, for run() to call at a moment of its choosing.

    Use it at the bottom of a lesson file:

        if __name__ == "__main__":
            run(main)
    """
    try:
        main_fn()
    except (KeyboardInterrupt, EOFError):
        # Ctrl+C / Ctrl+D — a deliberate exit, so leave quietly instead of with a traceback
        print()
    except anthropic.AuthenticationError:
        sys.exit("Invalid API key.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited. Wait and retry.")
    except anthropic.APIStatusError as err:   # any other bad status: 400, 404, 5xx
        sys.exit(f"API error {err.status_code}: {err.message}")
    except anthropic.APIConnectionError:      # never reached the server (network/DNS/timeout)
        sys.exit("Network error. Check your connection.")


# ── messages ─────────────────────────────────────────────────────────────────────────

# The API is stateless: it remembers nothing between calls, so the conversation is a plain
# Python list that you own and resend in full every time. These two just append the right
# shape to it. They return None and mutate the list in place — which is why you call
# add_user_message(messages, "hi") and then keep using `messages`, rather than assigning
# the result to anything.

def add_user_message(messages: list, prompt: str) -> None:
    messages.append({"role": "user", "content": prompt})


# `text` here is Claude's reply, not a prompt — a prompt is something you send.
def add_assistant_message(messages: list, text: str) -> None:
    messages.append({"role": "assistant", "content": text})


# ── calling Claude ───────────────────────────────────────────────────────────────────

def chat(
    client: anthropic.Anthropic,
    messages: list,
    model: str = MODEL,
    max_tokens: int = MAX_TOKENS,
    system=anthropic.omit,
    stop_sequences=anthropic.omit,
    tracker: UsageTracker | None = None,
) -> str:
    """One request, text of the reply back.

    `client` and `messages` are required — everything after them has a default, so a plain
    call is just `chat(client, messages)` and the extras are there when a lesson needs one.

    anthropic.omit, not None: the SDK drops an omitted field from the JSON body entirely,
    whereas None is sent as a literal `null` and the API rejects it.
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=messages,
        system=system,
        stop_sequences=stop_sequences,
    )

    if tracker is not None:
        tracker.record(response)

    # response.content is a LIST of blocks, not a string, and not every block is text — a
    # reply can also carry tool_use or thinking blocks. Filter by type, then join.
    return "".join(block.text for block in response.content if block.type == "text")


def ask(client: anthropic.Anthropic, prompt: str, **kwargs) -> str:
    """One prompt in, one reply out — for the common case with no conversation history.

    Builds the throwaway messages list itself, so a lesson comparing two prompt wordings
    doesn't need three lines of setup each time. Anything chat() accepts can still be
    passed through (system=..., tracker=..., model=...).
    """
    messages = []
    add_user_message(messages, prompt)
    return chat(client, messages, **kwargs)


# ── comparing prompts ────────────────────────────────────────────────────────────────

def compare(client: anthropic.Anthropic, prompts: dict[str, str],
            tracker: UsageTracker | None = None, **kwargs) -> dict[str, str]:
    """Run several wordings of the same request and print each reply under its label.

    The whole shape of this module is "here is a weak prompt, here is a stronger one" — so
    take a {label: prompt} dict, run them all, and return {label: reply} in case a lesson
    wants to do something further with the answers.

    Reading two replies side by side is an impression, not a measurement. When an
    improvement actually needs proving, that's what ../prompt-evaluation/ is for.
    """
    results = {}

    for label, prompt in prompts.items():
        print(f"\n{'─' * 70}\n{label}\n{'─' * 70}")
        reply = ask(client, prompt, tracker=tracker, **kwargs)
        print(reply)
        results[label] = reply

    return results
