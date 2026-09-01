"""Sending tool results.

Running the function and returning what it produced, as a tool_result block matching the
tool_use_id. Tool results go back under the user role, which reads oddly the first time.
"""

# After Claude requests a tool call, you need to execute the function and send the results back. 
# This completes the tool use workflow by providing Claude with the information it requested.

# Tool Result Block

# After running the tool function, you need to send the results back to Claude using a tool result block. 
# This block goes inside a user message and tells Claude what happened when you executed the tool.

# The tool result block has several important properties:

# - tool_use_id - Must match the id of the ToolUse block that this ToolResult corresponds to
# - content - Output from running your tool, serialized as a string
# - is_error - True if an error occurred

# Handling Multiple Tool Calls

# Claude can request multiple tool calls in a single response. 
# For example, if a user asks "What's 10 + 10 and what's 30 + 30?", 
# Claude might respond with two separate ToolUse blocks.
# Each tool call gets a unique ID, and you must match these IDs when sending back results. 
# This ensures Claude knows which result corresponds to which request, even if the results arrive in a different order.

# Building the Follow-up Request
# Your follow-up request to Claude must include the complete conversation history plus the new tool result. 
# Here's the structure:

# messages.append({
#     "role": "user",
#     "content": [{
#         "type": "tool_result",
#         "tool_use_id": response.content[1].id,
#         "content": "15:04:22",
#         "is_error": False
#     }]
# })
# The complete message history now contains:
# Original user message
# Assistant message with tool use block
# User message with tool result block

# Making the Final Request

# When sending the follow-up request, you must still include the tool schema even though you're not expecting Claude to make another tool call. 
# Claude needs the schema to understand the tool references in your conversation history.

# client.messages.create(
#     model=model,
#     max_tokens=1000,
#     messages=messages,
#     tools=[get_current_datetime_schema]
# )

# Claude will then respond with a final message that incorporates the tool results into a natural response for the user


# ─────────────────────────────────────────────────────────────────────────────────────
# The full round trip, finally closed:
#
#   user question + tool schemas
#         ↓
#   assistant: [ ..., tool_use(id=toolu_x, name, input) ]   stop_reason="tool_use"
#         ↓
#   YOU run the real function                               ← the only step Claude can't do
#         ↓
#   user: [ tool_result(tool_use_id=toolu_x, content, is_error) ]
#         ↓
#   assistant: the actual answer                            stop_reason="end_turn"
#
# Three rules the API enforces, and one it doesn't:
#
#   * tool_use_id must match, exactly. It is the only link between request and result.
#   * content must be a STRING. A dict or an int is a 400 — serialize it yourself.
#   * the follow-up call must STILL pass tools=. The history refers to a tool, so the
#     definition has to be there for it to resolve, even though no new call is expected.
#   * (not enforced) every tool_use block needs its own tool_result, in the SAME user
#     message. Miss one and the API rejects the turn.
# ─────────────────────────────────────────────────────────────────────────────────────

from helpers import (
    UsageTracker,
    add_assistant_message,
    add_user_message,
    chat,
    get_client,
    run,
    text_from,
    tool_uses,
)
# run_tool and the registry live in tools.py — every later lesson needs them, and a
# numbered file cannot be imported.
from tools import get_current_datetime_schema, run_tool

MODEL = "claude-sonnet-5"


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    messages = []
    add_user_message(messages, "What is the exact time, formatted as HH:MM:SS?")

    response = chat(client, messages, tools=[get_current_datetime_schema], tracker=tracker)
    print(f"1. stop_reason={response.stop_reason}  blocks={[b.type for b in response.content]}")

    # Whole thing back in, untouched — the tool_result below quotes an id that only exists
    # inside this block list.
    add_assistant_message(messages, response.content)

    # One result per tool_use block, all in ONE user message. A list comprehension rather
    # than a loop with a single variable, because a reply can carry several.
    results = [run_tool(block) for block in tool_uses(response)]
    for block, result in zip(tool_uses(response), results):
        print(f"2. ran {block.name}({block.input}) -> {result['content']!r} "
              f"is_error={result['is_error']}")

    add_user_message(messages, results)

    # tools= again. The history now mentions a tool, so the definition has to travel with it.
    final = chat(client, messages, tools=[get_current_datetime_schema], tracker=tracker)
    print(f"3. stop_reason={final.stop_reason}")
    print(f"\nClaude: {text_from(final).strip()}")

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
