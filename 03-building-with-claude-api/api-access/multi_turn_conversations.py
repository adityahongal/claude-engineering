"""Multi-turn conversations with the Messages API.

The API is stateless, so the conversation is a list you maintain yourself: append
each user message, append Claude's reply, and resend the whole list every call.
"""

# Claude doesn't store any of your conversation history.
# Each request you make is completely independent, with no memory of previous exchanges.
# This means if you want to have a multi-turn conversation where Claude remembers context from earlier messages, 
# you need to handle the conversation state yourself.

# The problem with stateless conversations

# Let's say you ask Claude "What is quantum computing?" and get a good response. 
# Then you follow up with "Write another sentence" - Claude has no idea what you're referring to. 
# It will write a sentence about something completely random because it has no memory of the quantum computing discussion.

# To maintain conversation context, you need to do two things:

# Manually maintain a list of all messages in your code
# Send the complete message history with every request

# Here's the flow:

# 1.Send your initial user message to Claude
# 2.Take Claude's response and add it to your message list as an assistant message
# 3.Add your follow-up question as another user message
# 4.Send the entire conversation history to Claude

import os
import sys

import anthropic
from dotenv import load_dotenv

MODEL = "claude-sonnet-5"
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

# Both helpers mutate the list in place and return None. That works because a list is
# passed by reference — `messages` in here is the SAME object as in main(), not a copy,
# and `.append()` changes that object.
# Careful: `messages = messages + [msg]` would rebind the local name only, and main()
# would never see the new message.

def chat(client: anthropic.Anthropic, messages: list) -> str:
    # `response` (singular) is what comes back; `messages` (plural) is the history going
    # up. Two names one letter apart is how the two get mixed up.
    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages
    )

    # Iterate response.content — the list of blocks. Iterating the response OBJECT gives
    # (field_name, value) tuples, because it's a Pydantic model, and a tuple has no .type
    return "".join(block.text for block in response.content if block.type == "text")


def main():

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()


    # Start with an empty message list
    messages = []

    try:
        # Add the initial user question
        add_user_message(messages, "Define quantum computing in one sentence")

        # Get Claude's response
        answer = chat(client, messages)
        print("Turn 1:", answer)

        # Add Claude's response to the conversation history
        add_assistant_message(messages, answer)

        # Add a follow-up question
        add_user_message(messages, "Write another sentence")

        # Get the follow-up response with full context — all 3 messages go up this time
        final_answer = chat(client, messages)

        print("Turn 2:", final_answer)

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