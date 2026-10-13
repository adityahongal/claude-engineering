"""Building the message list, calling Claude, and reading what comes back."""

import anthropic
from anthropic.types import Message

from .client import MAX_TOKENS, MODEL
from .usage import UsageTracker


# ── messages ─────────────────────────────────────────────────────────────────────────

# The API is stateless: the conversation is a list you own and resend in full every time.
# Both builders take a string, a list of content blocks, or a whole Message — the last so
# a loop can write add_assistant_message(messages, response) without reaching for .content.

def _content_of(message):
    return message.content if isinstance(message, Message) else message


def add_user_message(messages: list, message) -> None:
    """tool_result blocks go under "user" too — the role means "not the model"."""
    messages.append({"role": "user", "content": _content_of(message)})


def add_assistant_message(messages: list, message) -> None:
    """Claude's reply goes back verbatim — tool_use, thinking and compaction blocks
    included. Keeping only the text breaks whatever refers to the blocks dropped."""
    messages.append({"role": "assistant", "content": _content_of(message)})


# ── calling Claude ───────────────────────────────────────────────────────────────────

def chat(client: anthropic.Anthropic, messages: list, *, model: str = MODEL,
         max_tokens: int = MAX_TOKENS, tracker: UsageTracker | None = None,
         **params) -> Message:
    """One request; the WHOLE response back.

    Anything else — system=, tools=, thinking=, output_config=, cache_control= — goes
    straight through to messages.create(). Leave a parameter out rather than passing None:
    None is sent as a literal null and rejected.
    """
    response = client.messages.create(model=model, max_tokens=max_tokens,
                                      messages=messages, **params)
    if tracker is not None:
        tracker.record(response)
    return response


def chat_text(client: anthropic.Anthropic, messages: list, **kwargs) -> str:
    """chat(), reduced to the reply's text — for when text is all the lesson wants."""
    return text_from(chat(client, messages, **kwargs))


def ask(client: anthropic.Anthropic, prompt: str, **kwargs) -> str:
    """One prompt in, the reply's text out, no history to manage."""
    return chat_text(client, [{"role": "user", "content": prompt}], **kwargs)


# ── reading a response ───────────────────────────────────────────────────────────────

def text_from(response: Message) -> str:
    """The text blocks, joined with "" — consecutive text blocks are often one sentence
    split at citation boundaries, and a newline would break it apart."""
    return "".join(block.text for block in response.content if block.type == "text")


def tool_uses(response: Message) -> list:
    """Every tool_use block, in order. A list: one reply can ask for several."""
    return [block for block in response.content if block.type == "tool_use"]


def wants_tool(response: Message) -> bool:
    """stop_reason is the loop condition — not the text, not the block shapes."""
    return response.stop_reason == "tool_use"
