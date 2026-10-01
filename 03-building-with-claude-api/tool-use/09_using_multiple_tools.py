"""Using multiple tools.

More than one tool available at once — routing by tool name, and handling a reply that
asks for several in a single turn.
"""
# This code shows how to integrate additional tools by following a simple pattern.

# The Tools We're Adding
# We need three main capabilities for our reminder system:

# Get current date time - Claude needs to know the current date and time
# Add duration to date time - Claude isn't perfect with date time addition
# Set a reminder - Need a way to set a reminder

# The good news is that most of the implementation work is already done. 
# The add_duration_to_datetime function and set_reminder function are provided, along with their corresponding schemas.

# Adding Tools to the Conversation
# First, update the run_conversation function to include the new tool schemas in the tools list:

# response = chat(messages, tools=[
#     get_current_datetime_schema,
#     add_duration_to_datetime_schema,
#     set_reminder_schema
# ])
# This tells Claude about all three available tools it can use during the conversation.

# Updating the Tool Router
# Next, modify the run_tool function to handle the new tool calls. 
# Add elif cases for each new tool:

# def run_tool(tool_name, tool_input):
#     if tool_name == "get_current_datetime":
#         return get_current_datetime(**tool_input)
#     elif tool_name == "add_duration_to_datetime":
#         return add_duration_to_datetime(**tool_input)
#     elif tool_name == "set_reminder":
#         return set_reminder(**tool_input)
    
# The pattern is simple: check the tool name, call the corresponding function with the provided input, and return the result.

# Testing Multiple Tool Usage:

# To test the system, try a request that requires multiple tools: "Set a reminder for my doctors appointment. Its 177 days after Jan 1st, 2050."
# This request forces Claude to:
# 1. Calculate the date (using add_duration_to_datetime)
# 2. Set the reminder (using set_reminder)

# Claude handles this by first explaining what it needs to do, then making the appropriate tool calls in sequence. 
# The conversation shows Claude calculating June 27, 2050 as the target date, then setting the reminder for that date.

# Understanding the Message Flow:

# When you examine the conversation history, you'll see the complete message structure:
# - User message with the request
# - Assistant message containing both text and tool use blocks
# - Tool result messages
# - Follow-up assistant messages

# The Simple Pattern for Adding Tools:

# Once you have the core tool infrastructure, adding new tools follows this pattern:

# 1.Create the tool function implementation
# 2.Define the tool schema
# 3.Add the schema to the tools list in run_conversation
# 4. Add a case for the tool in run_tool

# This modular approach makes it easy to expand your AI assistant's capabilities without restructuring existing code. 
# Each new tool integrates seamlessly with the existing conversation flow and tool-handling logic.

# ─────────────────────────────────────────────────────────────────────────────────────
# Where this repo already was, and what actually changed.
#
# The course's four-step pattern, mapped onto this folder:
#
#   1. the function             set_reminder()            tools.py
#   2. its schema               set_reminder_schema       tools.py
#   3. add it to the tools list ALL_SCHEMAS               tools.py
#   4. add a case to run_tool   TOOL_FUNCTIONS            tools.py
#
# All four land in one file, and run_conversation does not change at all — it takes
# whatever list it is handed. That is the payoff of 08 living in helpers.py.
#
# Step 4 is a dict entry, not an elif. The course's if/elif chain grows a branch per tool
# and repeats `return fn(**tool_input)` in every one; the dict is the same routing as data.
# An unknown name is one .get() returning None, already answered with is_error=True.
#
# The four steps are also four ways to forget something, and nothing fails until Claude
# calls the tool that was missed — mid-conversation, as a confusing error. check_registry()
# turns each one into a failure BEFORE any API call: schema without a function, function
# without a schema, parameters that don't match properties, a wrong "required" list. It
# is 04's check, generalised to every tool.
#
# set_reminder is "provided" in the course; this one is written here, and differs on
# purpose:
#   * it stores the reminder in REMINDERS — a real side effect — so this file can check
#     afterwards that a reminder EXISTS, rather than trusting Claude saying "Done".
#   * it returns a dict, the first tool that does — so run_tool's json.dumps path finally
#     runs for real.
#   * it rejects a timestamp in the past. That error is something Claude can act on.
# ─────────────────────────────────────────────────────────────────────────────────────

import sys

from helpers import UsageTracker, get_client, run, run_conversation, text_from
from tools import ALL_SCHEMAS, REMINDERS, check_registry

MODEL = "claude-sonnet-5"


def show_turn(turn, response, results):
    print(f"  turn {turn}: stop_reason={response.stop_reason}  "
          f"blocks={[b.type for b in response.content]}")
    for block, result in zip([b for b in response.content if b.type == "tool_use"],
                             results or []):
        print(f"          {block.name}({block.input}) -> {result['content']!r}"
              + ("  [ERROR]" if result["is_error"] else ""))


def ask(client, tracker, question):
    print(f"\n> {question}")
    messages = [{"role": "user", "content": question}]
    final = run_conversation(client, messages, tools=ALL_SCHEMAS, tracker=tracker,
                             on_turn=show_turn)
    print(f"\nClaude: {text_from(final).strip()}")


def main():
    # Before spending a token: are the four steps in agreement for every tool?
    problems = check_registry()
    if problems:
        sys.exit("tool registry is inconsistent:\n  " + "\n  ".join(problems))
    print(f"registry ok: {[s['name'] for s in ALL_SCHEMAS]}")

    client = get_client()
    tracker = UsageTracker(MODEL)

    # The course's test. A fixed start date, so no clock needed: date arithmetic, then the
    # reminder. Jan 1st + 177 days is June 27th, 2050.
    ask(client, tracker,
        "Set a reminder for my doctors appointment. Its 177 days after Jan 1st, 2050.")

    # All three tools: "Thursday" means nothing without today's date, and the weekday has
    # to come from somewhere — get_current_datetime's default output does not include it.
    ask(client, tracker, "Remind me to renew my passport a week from this Thursday, at 9am.")

    # The proof. Claude saying "I've set it" is text; this is the side effect.
    print("\nreminders actually stored:")
    for reminder in REMINDERS:
        print(f"  #{reminder['id']}  {reminder['timestamp']}  {reminder['content']}")

    print()
    tracker.report()


if __name__ == "__main__":
    run(main)
