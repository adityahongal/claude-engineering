"""Multi-turn conversations with tools.

Keeping the history intact across a tool call. Claude's tool_use reply has to go back in
unchanged, or the tool_result that follows refers to nothing.
"""

# When building applications with multiple tools, you need to handle scenarios where Claude might need to call several tools in sequence to answer a single user question.
# For example, if a user asks "What day is 103 days from today?", Claude needs to first get the current date, then add 103 days to it.

# This creates a multi-turn conversation pattern where Claude makes multiple tool requests before providing a final answer.
# Your application needs to handle this automatically.

# The Multi-Turn Tool Pattern
# Here's what happens behind the scenes when Claude needs multiple tools:

# 1. User asks: "What day is 103 days from today?"
# 2. Claude responds with a tool use block requesting get_current_datetime
# 3. Your server calls the function and returns the result
# 4. Claude realizes it needs more information and requests add_duration_to_datetime
# 5. Your server calls that function and returns the result
# 6. Claude now has enough information to provide the final answer

# Building a Conversation Loop
# To handle this pattern, you need a conversation loop that continues until Claude stops requesting tools:

# def run_conversation(messages):
#     while True:
#         response = chat(messages)
#
#         add_assistant_message(messages, response)
#
#         # Pseudo code
#         if response isn't asking for a tool:
#             break
#
#         tool_result_blocks = run_tools(response)
#         add_user_message(messages, tool_result_blocks)
#
#     return messages

# Refactoring Helper Functions
# Before implementing the conversation loop, you need to update your helper functions to handle multiple message blocks properly.

# Updating Message Handlers
# Your add_user_message and add_assistant_message functions currently assume you're always working with plain text.
# Update them to handle full message objects:

# from anthropic.types import Message
#
# def add_user_message(messages, message):
#     user_message = {
#         "role": "user",
#         "content": message.content if isinstance(message, Message) else message
#     }
#     messages.append(user_message)

# This allows you to pass in either a string, a list of blocks, or a complete message object.

# Updating the Chat Function
# Modify your chat function to accept a list of tools and return the full message instead of just text:

# def chat(messages, system=None, temperature=1.0, stop_sequences=[], tools=None):
#     params = {
#         "model": model,
#         "max_tokens": 1000,
#         "messages": messages,
#         "temperature": temperature,
#         "stop_sequences": stop_sequences,
#     }
#     if tools:
#         params["tools"] = tools
#     if system:
#         params["system"] = system
#     message = client.messages.create(**params)
#     return message

# Extracting Text from Messages
# Since you're now returning full message objects, create a helper to extract text when needed:

# def text_from_message(message):
#     return "\n".join(
#         [block.text for block in message.content if block.type == "text"]
#     )

# Key Improvements
# - Flexible message handling - Your helper functions can now work with different message formats
# - Tool support in chat - The chat function can receive and pass through tool schemas
# - Full message returns - You get complete message objects instead of just text, preserving all blocks
# - Text extraction utility - Easy way to get readable text from complex messages


# ─────────────────────────────────────────────────────────────────────────────────────
# Where this repo already was, and what actually changed.
#
# Most of the refactor above landed in helpers.py back in lesson 05, because tool use
# needed it from the first call:
#
#   chat() returns the whole Message      already — since 05
#   chat() takes tools=                   already — and via anthropic.omit, not
#                                         `if tools:`, which does the same job in one line
#   text_from()                           already — joined with "" rather than "\n"
#   add_*_message() takes a Message       NEW in this lesson
#
# The last one is what the loop needs: `add_assistant_message(messages, response)` with the
# response itself, no `.content` to remember. Pass a raw Message without that change and
# the request fails — a Message object is not a valid content value.
#
# The other new piece is in tools.py: add_duration_to_datetime, the second tool in the
# chain. Without it, the scenario this lesson describes cannot happen — Claude would get
# the date and then do the arithmetic itself, which is exactly the thing it is bad at.
#
# A bug in the course slide, not in the summary: the slide's loop says
# `add_user_message(messages, response)` straight after chat(). That files Claude's own
# reply under the user role. It has to be add_assistant_message.
# ─────────────────────────────────────────────────────────────────────────────────────
#
# This file walks the turns BY HAND, with no while loop. That is deliberate: the same four
# steps repeat for every turn, and you cannot know in advance how many turns there will
# be. Writing them out is the argument for the loop in 08.
#
#   user:      "What day is 103 days from today?"
#   assistant: [tool_use get_current_datetime]              stop_reason=tool_use
#   user:      [tool_result "2026-10-01 11:20:04"]
#   assistant: [tool_use add_duration_to_datetime]          stop_reason=tool_use
#   user:      [tool_result "2027-01-12 11:20:04 (Tuesday)"]
#   assistant: "103 days from today is ..."                 stop_reason=end_turn
#
# Every call sends the WHOLE list above, schemas included — the third call pays for
# everything the first two produced.

from helpers import (
    UsageTracker,
    add_assistant_message,
    add_user_message,
    chat,
    get_client,
    run,
    text_from,
    tool_uses,
    wants_tool,
)
from tools import ALL_SCHEMAS, run_tool

MODEL = "claude-sonnet-5"


def take_turn(client, messages, tracker, turn):
    """One round: ask Claude, record its reply, and answer any tools it asked for.

    These four steps are the body of the loop in 08. Here they are called by hand.
    """
    response = chat(client, messages, tools=ALL_SCHEMAS, tracker=tracker)

    # The Message itself, not response.content — the refactor this lesson is about.
    add_assistant_message(messages, response)

    print(f"turn {turn}: stop_reason={response.stop_reason}  "
          f"blocks={[b.type for b in response.content]}")

    if not wants_tool(response):
        return response

    results = [run_tool(block) for block in tool_uses(response)]
    for block, result in zip(tool_uses(response), results):
        print(f"        ran {block.name}({block.input}) -> {result['content']!r}"
              + ("  [ERROR]" if result["is_error"] else ""))
    add_user_message(messages, results)

    return response


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    messages = []
    add_user_message(messages, "What day is 103 days from today?")

    # Written out three times on purpose. Each `if` is the question the loop asks on every
    # pass — is Claude still waiting on a tool? — and there is no way to know beforehand
    # how many times it will be yes.
    response = take_turn(client, messages, tracker, turn=1)
    if wants_tool(response):
        response = take_turn(client, messages, tracker, turn=2)
    if wants_tool(response):
        response = take_turn(client, messages, tracker, turn=3)

    if wants_tool(response):
        # Three turns was a guess, and here it ran out. That guess is what 08 replaces.
        print("\nClaude still wants a tool after 3 turns — the hand-written version ran "
              "out of turns.")
    else:
        print(f"\nClaude: {text_from(response).strip()}")

    print("\nhistory:")
    for message in messages:
        content = message["content"]
        shape = "text" if isinstance(content, str) else [
            b["type"] if isinstance(b, dict) else b.type for b in content
        ]
        print(f"  {message['role']:9} -> {shape}")

    tracker.report()


if __name__ == "__main__":
    run(main)
