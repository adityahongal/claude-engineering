"""Structured data — getting clean output with no commentary around it.

Two approaches, one obsolete and one current:

  * prefill + stop_sequences — what the lesson teaches. You end the message list on a
    deliberately unfinished assistant turn, so Claude continues from it rather than
    introducing itself. Returns a 400 on claude-sonnet-5, claude-opus-5 and the 4.6-4.8
    family; still accepted by claude-haiku-4-5, which is why that half uses Haiku.

  * output_format + a Pydantic model — the API is constrained to your schema, so there is
    no fence to strip and nothing to parse. This is what you'd reach for now.

Both are here on purpose: the first records what the course taught and why it stopped
working, the second is the replacement.
"""

# When you need Claude to generate structured data like JSON, Python code, or bulleted lists,
# you'll often run into a common problem: Claude wants to be helpful and add explanatory text around your content.
# While this is usually great, sometimes you need just the raw data with nothing else.

# The Problem with Default Responses
# Example
# By default, when you ask Claude to generate JSON, you might get something like this:

# ```json
# {
#   "source": ["aws.ec2"],
#   "detail-type": ["EC2 Instance State-change Notification"],
#   "detail": {
#     "state": ["running"]
#   }
# }
# ```

# The JSON is correct, but it's wrapped in markdown formatting and includes explanatory text.
# For a web app where users need to copy the raw JSON, this creates friction in the user experience.

# The Solution: Assistant Message Prefilling + Stop Sequences
# You can combine assistant message prefilling with stop sequences to get exactly the content you want. Here's how it works:

# messages = []

# add_user_message(messages, "Generate a very short event bridge rule as json")
# add_assistant_message(messages, "```json")

# text = chat(messages, stop_sequences=["```"])

# This technique works by:
# The user message tells Claude what to generate
# The prefilled assistant message makes Claude think it already started a markdown code block
# Claude continues by writing just the JSON content
# When Claude tries to close the code block with ```, the stop sequence immediately ends generation

# The result is clean JSON with no extra formatting:

# {
#   "source": ["aws.ec2"],
#   "detail-type": ["EC2 Instance State-change Notification"],
#   "detail": {
#     "state": ["running"]
#   }
# }

# This technique isn't limited to JSON generation.
# Use it anytime you need structured data without commentary:
# Python code snippets
# Bulleted lists
# CSV data
# Any formatted content where you want just the content, not explanations

# The key is identifying what Claude naturally wants to wrap your content in, then using that as your prefill and stop sequence.


import os
import sys

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

MODEL = "claude-sonnet-5"
LEGACY_MODEL = "claude-haiku-4-5"    # prefill is still accepted here, not on MODEL
MAX_TOKENS = 1024

# helper functions

def add_user_message(messages, prompt):
    user_message = {
        "role" : "user",
        "content" : prompt
    }

    messages.append(user_message)

# `text` here is Claude's reply, not a prompt — a prompt is something you send.
def add_assistant_message(messages, text):
    assistant_message = {
        "role" : "assistant",
        "content" : text
    }
    messages.append(assistant_message)


def chat(client: anthropic.Anthropic, messages: list, model: str = MODEL,
         stop_sequences = anthropic.omit) -> str:
    # `anthropic.omit` again rather than None — an absent stop_sequences must be left out
    # of the request, not sent as a null.
    response = client.messages.create(
        model = model,
        max_tokens = MAX_TOKENS,
        messages = messages,
        stop_sequences = stop_sequences
    )

    return "".join(block.text for block in response.content if block.type == "text")


# ---------------------------------------------------------------------------
# 1. The lesson's technique: prefill + stop sequence
# ---------------------------------------------------------------------------

def prefill_technique(client: anthropic.Anthropic) -> str:
    messages = []
    add_user_message(messages, "Generate a very short event bridge rule as json")

    # NOT a stored reply. This is a deliberately unfinished assistant turn — Claude sees
    # itself mid-sentence having just opened a code fence, so it continues with JSON
    # instead of "Sure! Here's a rule:".
    add_assistant_message(messages, "```json")

    # Generation stops the moment Claude tries to close the fence, so the closing ``` and
    # anything after it never arrive.
    return chat(client, messages, model=LEGACY_MODEL, stop_sequences=["```"])


# ---------------------------------------------------------------------------
# 2. The current technique: constrain generation to a schema
# ---------------------------------------------------------------------------

class EventBridgeRule(BaseModel):
    source: list[str]
    detail: dict
    # A field like "detail-type" can't be a Python name — it would need
    # Field(alias="detail-type"). Left out here to keep the schema readable.


def structured_output(client: anthropic.Anthropic) -> EventBridgeRule:
    messages = []
    add_user_message(messages, "Generate a very short EventBridge rule for EC2 state changes.")

    # messages.parse() instead of create(): the schema is sent with the request and the
    # response is validated into the model for you. No fences, no stop sequences.
    response = client.messages.parse(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        output_format = EventBridgeRule,
    )

    return response.parsed_output      # already an EventBridgeRule, not a string


def main():

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()

    # No loop here — two one-shot calls. A while-loop with no input() and no break would
    # hammer the API for as long as the process runs.
    try:
        print("prefill + stop_sequences  (Haiku — deprecated technique)")
        print("-" * 60)
        print(prefill_technique(client))

        print()
        print("output_format + Pydantic  (Sonnet — current technique)")
        print("-" * 60)
        rule = structured_output(client)
        print(rule)                    # a validated model object
        print(rule.model_dump())       # back to a plain dict, same as your Day 5 work

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

if __name__ == "__main__":
    main()
