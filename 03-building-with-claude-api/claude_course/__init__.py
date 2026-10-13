"""Shared plumbing for the course modules, from claude-features/ onwards.

The earlier modules each carry their own helpers.py — prompt-engineering/ and tool-use/
keep theirs, unchanged, because their lesson files and committed results were written
against them. This package is where that copying stops: one implementation, installed
once, imported from anywhere.

    from claude_course import get_client, run, chat, chat_text, UsageTracker

What it settles that the copies could not:

  * chat() returns the whole Message; chat_text() returns its text. prompt-engineering's
    chat() returned str and tool-use's returned Message — the same name with two meanings,
    which is why those were copies. Here they are two names.
  * chat() passes any extra keyword straight to messages.create(), so thinking=,
    output_config=, cache_control= or tools= work without the wrapper growing a parameter
    for each feature.
  * UsageTracker counts prompt-caching tokens, which the prompt-evaluation original does
    not — and claude-features/ is where caching is taught.
"""

from .client import MAX_TOKENS, MODEL, get_client, run
from .conversation import (
    add_assistant_message,
    add_user_message,
    ask,
    chat,
    chat_text,
    text_from,
    tool_uses,
    wants_tool,
)
from .tools import run_conversation, run_tool, run_tools, tool_result
from .usage import PRICES, UsageTracker

__all__ = [
    "MAX_TOKENS", "MODEL", "get_client", "run",
    "add_assistant_message", "add_user_message", "ask", "chat", "chat_text",
    "text_from", "tool_uses", "wants_tool",
    "run_conversation", "run_tool", "run_tools", "tool_result",
    "PRICES", "UsageTracker",
]
