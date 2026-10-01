"""Implementing multiple turns.

The loop: call, check whether Claude wants a tool, run it, send the result, repeat until
it stops asking. stop_reason == 'tool_use' is the condition.
"""

# Detecting Tool Requests
# The key to knowing whether Claude wants to use a tool lies in the stop_reason field of the response message. 
# When Claude decides it needs to call a tool, this field gets set to "tool_use". 
# This gives us a clean way to check if we need to continue the conversation loop:

# if response.stop_reason != "tool_use":
#     break  # Claude is done, no more tools needed

# THE CONVERSATIONAL LOOP
# The main conversation function follows a simple pattern:

# def run_conversation(messages):
#     while True:
#         response = chat(messages, tools=[get_current_datetime_schema])
#         add_assistant_message(messages, response)
#         print(text_from_message(response))
        
#         if response.stop_reason != "tool_use":
#             break
            
#         tool_results = run_tools(response)
#         add_user_message(messages, tool_results)
    
#     return messages
# This loop continues until Claude provides a final answer without requesting any tools.

# Handling Multiple Tool Calls

# Claude can request multiple tools in a single response. 
# The message content contains a list of blocks, and we need to process each tool use block separately
# The run_tools function handles this by filtering for tool use blocks and processing each one:

# def run_tools(message):
#     tool_requests = [
#         block for block in message.content if block.type == "tool_use"
#     ]
#     tool_result_blocks = []
    
#     for tool_request in tool_requests:
#         # Process each tool request...

# Tool Result Blocks

# Each tool use block must be answered with a corresponding tool result block. 
# The connection between them is maintained through matching IDs
# The tool result block structure includes:

# tool_result_block = {
#     "type": "tool_result",
#     "tool_use_id": tool_request.id,
#     "content": json.dumps(tool_output),
#     "is_error": False
# }

# Error Handling

# Robust tool execution requires handling potential errors. 
# When a tool fails, we still need to provide a result block to Claude:

# try:
#     tool_output = run_tool(tool_request.name, tool_request.input)
#     tool_result_block = {
#         "type": "tool_result",
#         "tool_use_id": tool_request.id,
#         "content": json.dumps(tool_output),
#         "is_error": False
#     }
# except Exception as e:
#     tool_result_block = {
#         "type": "tool_result", 
#         "tool_use_id": tool_request.id,
#         "content": f"Error: {e}",
#         "is_error": True
#     }

# Complete Workflow

# The complete multi-turn conversation works like this:

# 1. Send user message to Claude with available tools
# 2. Claude responds with text and/or tool requests
# 3. Execute all requested tools and create result blocks
# 4. Send tool results back as a user message
# 5. Repeat until Claude provides a final answer

# This creates a seamless experience where Claude can use multiple tools across several turns to fully answer complex user requests. 
# The conversation history maintains the complete context, allowing Claude to build upon previous tool results to provide comprehensive responses.

# ─────────────────────────────────────────────────────────────────────────────────────
# 07 wrote the turns out by hand and had to guess how many there would be. The loop
# removes the guess — it runs until stop_reason says Claude is done:
#
#   while Claude wants a tool:          stop_reason == "tool_use"
#       run every tool it asked for     run_tools() -> one tool_result per tool_use
#       send them all back              one user message
#   return the final response           stop_reason == "end_turn"
#
# Where this differs from the course code, and why:
#
#   * run_conversation lives in helpers.py and run_tools in tools.py, not here — 09 needs
#     both, and a numbered file cannot be imported.
#   * run_tool(block) takes the whole block, not (name, input). It needs block.id to build
#     the tool_result, so splitting the block apart just to hand back the id separately
#     buys nothing — and its try/except lives inside it, so every caller gets it for free.
#   * The course json.dumps() every output. json.dumps on a string wraps it in quotes, so
#     Claude would read '"2026-10-01"'. Strings go through as-is; only structured output
#     is dumped.
#   * The loop is CAPPED. `while True` trusts Claude to stop asking; a tool that keeps
#     failing, or a model that keeps re-checking, would loop and bill forever. Past the
#     cap it raises rather than returning — the last response is a tool request, not an
#     answer, and returning it would pass one off as the other.
#   * It returns the final response, not `messages`. The caller's list is extended in
#     place, so they already hold the history; what they want back is the answer.
# ─────────────────────────────────────────────────────────────────────────────────────

from helpers import UsageTracker, get_client, run, run_conversation, text_from
from tools import ALL_SCHEMAS

MODEL = "claude-sonnet-5"


def show_turn(turn, response, results):
    """Print what one pass of the loop did — the loop itself runs either way."""
    print(f"  turn {turn}: stop_reason={response.stop_reason}  "
          f"blocks={[b.type for b in response.content]}")
    for block, result in zip([b for b in response.content if b.type == "tool_use"],
                             results or []):
        print(f"          {block.name}({block.input}) -> {result['content']!r}"
              + ("  [ERROR]" if result["is_error"] else ""))


def ask(client, tracker, question, max_turns=10):
    print(f"\n> {question}")
    messages = [{"role": "user", "content": question}]
    final = run_conversation(client, messages, tools=ALL_SCHEMAS, tracker=tracker,
                             max_turns=max_turns, on_turn=show_turn)
    print(f"\nClaude: {text_from(final).strip()}")
    print(f"({len(messages)} messages in the history)")


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    # 1. The 07 question again — same three turns, no guessing how many.
    ask(client, tracker, "What day is 103 days from today?")

    # 2. Several tools in ONE reply. Once Claude has today's date, the three additions are
    #    independent, so it can ask for all of them at once — run_tools answers each in the
    #    same user message.
    ask(client, tracker, "What are the dates 30, 60 and 90 days from today?")

    # 3. The cap. One turn is never enough for question 1, so this must raise rather than
    #    hand back a tool request dressed up as an answer.
    try:
        ask(client, tracker, "What day is 103 days from today?", max_turns=1)
    except RuntimeError as err:
        print(f"\nstopped by the cap: {err}")

    print()
    tracker.report()


if __name__ == "__main__":
    run(main)
