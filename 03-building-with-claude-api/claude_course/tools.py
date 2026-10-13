"""The client-side tool loop, from tool-use/ — generic, so it takes the tool functions as
an argument instead of reading a module-level registry."""

import json

import anthropic
from anthropic.types import Message

from .client import MAX_TOKENS, MODEL
from .conversation import add_assistant_message, add_user_message, chat, wants_tool
from .usage import UsageTracker

MAX_TURNS = 10


def tool_result(tool_use_id: str, content: str, is_error: bool = False) -> dict:
    return {"type": "tool_result", "tool_use_id": tool_use_id,
            "content": content, "is_error": is_error}


def run_tool(block, functions: dict) -> dict:
    """Run one tool_use block; ALWAYS return a tool_result.

    Claude is blocked waiting on this id, so a failure still has to come back as an answer
    — flagged is_error, with a message Claude can read and retry from.
    """
    function = functions.get(block.name)
    if function is None:
        return tool_result(block.id, f"No tool named {block.name!r}", is_error=True)
    try:
        output = function(**block.input)
    except Exception as err:   # deliberately broad: every failure must become an answer
        return tool_result(block.id, f"{type(err).__name__}: {err}", is_error=True)
    # content must be a string; json.dumps on a string would wrap it in quotes.
    content = output if isinstance(output, str) else json.dumps(output)
    return tool_result(block.id, content)


def run_tools(response: Message, functions: dict) -> list:
    """A tool_result for every tool_use in the reply — all of them go in ONE user message."""
    return [run_tool(block, functions)
            for block in response.content if block.type == "tool_use"]


def run_conversation(client: anthropic.Anthropic, messages: list, tools: list,
                     functions: dict, *, tracker: UsageTracker | None = None,
                     max_turns: int = MAX_TURNS, on_turn=None, model: str = MODEL,
                     max_tokens: int = MAX_TOKENS, **params) -> Message:
    """Call Claude, run what it asks for, repeat until it stops asking.

    `messages` is extended in place; the final response is returned. Capped: past
    max_turns it raises rather than hand back a tool request dressed as an answer.
    on_turn(turn, response, results) is called after each turn; results is None last.
    """
    for turn in range(1, max_turns + 1):
        response = chat(client, messages, tools=tools, tracker=tracker, model=model,
                        max_tokens=max_tokens, **params)
        add_assistant_message(messages, response)

        if not wants_tool(response):
            if on_turn:
                on_turn(turn, response, None)
            return response

        results = run_tools(response, functions)
        add_user_message(messages, results)
        if on_turn:
            on_turn(turn, response, results)

    raise RuntimeError(
        f"Claude was still asking for tools when the {max_turns}-turn cap ran out"
    )
