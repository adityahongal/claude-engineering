# Response Streaming

# With streaming enabled, Claude immediately sends back an initial response indicating it has received your request and is starting to generate text. 
# Then you receive a series of events, each containing a small piece of the overall response.

# Your server can forward these text chunks to your client application as they arrive, allowing users to see the response building up word by word. 
# All of these events are part of a single request to Claude.

# Understanding Stream Events
# When you enable streaming, Claude sends back several types of events:

# MessageStart - A new message is being sent
# ContentBlockStart - Start of a new block containing text, tool use, or other content
# ContentBlockDelta - Chunks of the actual generated text   --> important
# ContentBlockStop - The current content block has been completed
# MessageDelta - The current message is complete
# MessageStop - End of information about the current message

# The ContentBlockDelta events contain the actual generated text that you'll want to display to users.

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
    with client.messages.stream(              # 1. .stream() not .create()
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
    ) as stream:
        # text_stream is a generator — each loop yields the next chunk and pauses.
        for text in stream.text_stream:       # 2. loop the chunks as they arrive
            # end="" so chunks flow into one paragraph; flush=True so they appear
            # immediately instead of sitting in Python's stdout buffer.
            print(text, end="", flush=True)
        print()
        return stream.get_final_text()        # 3. the assembled text, for the history


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