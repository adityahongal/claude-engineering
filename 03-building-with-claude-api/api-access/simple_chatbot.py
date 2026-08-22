"""A simple chatbot loop over the Messages API.

Reads input, appends it to the history, sends the whole history, prints the reply,
and appends that too — one exchange per iteration until the user quits.
"""

# we are using previous helper functions learnt so far to build a simple chatbot that takes user input and stay in loop until we interrupt

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

def chat(client: anthropic.Anthropic, messages: list) -> str:

    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages
    )

    return "".join(block.text for block in response.content if block.type == "text")


def main():

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()


    # Start with an empty message list
    messages = []

    try:
        while True:

            user_input = input("> ")                                #inbuilt input function
            # print("> ",user_input)

            # a way out that isn't Ctrl+C
            if user_input.lower() in ("quit", "exit"):
                break

            # Add this turn's message to the history
            add_user_message(messages, user_input)
            
            # Get Claude's response
            answer = chat(client, messages)
            print(answer)
            
            # Add Claude's response to the conversation history
            add_assistant_message(messages, answer)
            
            print("--------------------")

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