"""Handling message blocks.

Reading a reply that contains a tool_use block. response.content is a list, blocks carry
a type, and a single reply can hold text and tool_use together.
"""

# When working with Claude's tool functionality, you'll encounter a new type of response structure 
# that's different from the simple text responses you've seen before. 
# Instead of just getting back a single text block, Claude can now return multi-block messages that contain both text and tool usage information.

# Making Tool-Enabled API Calls

# To enable Claude to use tools, you need to include a tools parameter in your API call. Here's how to structure the request:
# messages = []
# messages.append({
#     "role": "user",
#     "content": "What is the exact time, formatted as HH:MM:SS?"
# })

# response = client.messages.create(
#     model=model,
#     max_tokens=1000,
#     messages=messages,
#     tools=[get_current_datetime_schema],                             # we add the tools schema here
# )
# The tools parameter takes a list of JSON schemas that describe the available functions Claude can call.

# Understanding Multi-Block Messages

# When Claude decides to use a tool, it returns an assistant message with multiple blocks in the content list
# A multi-block message typically contains: (important)

# 1. Text Block - Human-readable text explaining what Claude is doing (like "I can help you find out the current time. Let me find that information for you")
# 2. ToolUse Block - Instructions for your code about which tool to call and what parameters to use
    
# The ToolUse block includes:

# - An ID for tracking the tool call
# - The name of the function to call (like "get_current_datetime")
# - Input parameters formatted as a dictionary
# - The type designation "tool_use"

# Managing Conversation History with Multi-Block Messages(important)

# Remember that Claude doesn't store conversation history - you need to manage it manually. 
# When working with tool responses, you must preserve the entire content structure, including all blocks.
# Here's how to properly append a multi-block assistant message to your conversation history:

# messages.append({
#     "role": "assistant",
#     "content": response.content
# })
# This preserves both the text block and the tool use block, which is crucial for maintaining the conversation context when you make subsequent API calls.

# The Complete Tool Usage Flow

# The tool usage process follows this pattern:
# 1.Send user message with tool schema to Claude
# 2.Receive assistant message with text block and tool use block
# 3.Extract tool information and execute the actual function
# 4.Send tool result back to Claude along with complete conversation history
# 5.Receive final response from Claude

# Each step requires careful handling of the message structure to ensure Claude has the full context it needs to provide accurate responses.


# ─────────────────────────────────────────────────────────────────────────────────────
# This file covers steps 1 and 2 only — send the question with a schema, and read what
# comes back. Running the function and returning the result is the next lesson.
#
#   messages + tools
#         ↓
#   response.content = [ TextBlock , ToolUseBlock ]     ← a LIST, two kinds of block
#         ↓
#   messages.append({"role": "assistant", "content": response.content})
#                                                       ↑ the whole list, untouched
#
# The helpers already handle both halves of this:
#
#   chat()                  returns the WHOLE response, not "".join(text blocks) — the
#                           tool_use block is the point, and joining text discards it
#   add_assistant_message() takes a string OR a list of blocks, so response.content goes
#                           back in verbatim
#   tool_uses()             every tool_use block, as a list
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
    wants_tool,
)
from tools import get_current_datetime_schema

MODEL = "claude-sonnet-5"


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    messages = []
    add_user_message(messages, "What is the exact time, formatted as HH:MM:SS?")

    # tools is a LIST of schemas, even when there is only one.
    response = chat(client, messages, tools=[get_current_datetime_schema], tracker=tracker)

    # stop_reason is the signal, not the text. "tool_use" means Claude has paused and is
    # waiting on you; "end_turn" means it considers itself finished.
    print(f"stop_reason: {response.stop_reason}   wants a tool: {wants_tool(response)}")

    # Walk the blocks rather than reaching for content[0]. The first block is usually text
    # here, but that is a habit of this model on this prompt, not a guarantee.
    print(f"\n{len(response.content)} block(s) in the reply:")
    for i, block in enumerate(response.content):
        print(f"  [{i}] type={block.type}")
        if block.type == "text":
            print(f"      text: {block.text.strip()}")
        elif block.type == "thinking":
            # NOT in the course notes above, and the first real surprise of the module.
            # The course describes a tool-use reply as [text, tool_use]. Two identical runs
            # of THIS file returned:
            #
            #     run 1:  [thinking, tool_use]
            #     run 2:  [tool_use]
            #
            # Never a text block, and not even the same shape twice. The block composition
            # is not part of the contract — only `stop_reason` and the presence of a
            # tool_use block are.
            #
            # A thinking block carries .thinking, NOT .text, so content[0].text — which the
            # course's mental model invites — raises AttributeError on run 1 and silently
            # picks the wrong block on run 2. Filtering by .type is the only thing that
            # survives both.
            print(f"      thinking: {block.thinking.strip()[:120]}...")
        elif block.type == "tool_use":
            # id is what the tool_result must quote back next lesson. name says which
            # function to call, input is the arguments Claude chose — already a dict, no
            # json.loads needed.
            print(f"      id:    {block.id}")
            print(f"      name:  {block.name}")
            print(f"      input: {block.input}")

    # The step that is easy to get wrong: response.content goes back WHOLE. Storing only
    # text_from(response) would drop the tool_use block, and the tool_result sent next
    # lesson would quote an id that no longer exists anywhere in the history.
    add_assistant_message(messages, response.content)

    print("\nhistory now:")
    for message in messages:
        content = message["content"]
        shape = content if isinstance(content, str) else [b.type for b in content]
        print(f"  {message['role']:9} -> {shape}")

    print(f"\ntool calls requested: {[b.name for b in tool_uses(response)]}")
    print(f"text alongside them:  {text_from(response).strip()!r}")

    tracker.report()


if __name__ == "__main__":
    run(main)
