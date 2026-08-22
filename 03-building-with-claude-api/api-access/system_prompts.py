# System prompts are a powerful way to customize how Claude responds to user input. 
# Instead of getting generic answers, you can shape Claude's tone, style, and approach to match your specific use case.

# Why System Prompts Matter

# Consider building a math tutor chatbot. When a student asks "How do I solve 5x + 2 = 3 for x?", 
# you want Claude to act like a real tutor, not just spit out the answer. 
# A good math tutor should:

# Initially give hints rather than complete solutions
# Patiently walk students through problems step by step
# Show solutions for similar problems as examples
    
# You definitely don't want Claude to:

# Immediately give direct answers
# Tell students to just use a calculator

# System prompts provide Claude with guidance on how to respond. 
# You define them as plain strings and pass them into the create function call. 
# 
# The key benefits are:
# System prompts provide Claude guidance on how to respond
# Claude will try to respond in the same way someone in the specified role would respond
# Helps keep Claude on task

# Here's the basic structure:

# system_prompt = """
# You are a patient math tutor.
# Do not directly answer a student's questions.
# Guide them to a solution step by step.
# """

# client.messages.create(
#     model=model,
#     messages=messages,
#     max_tokens=1000,
#     system=system_prompt
# )

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

# The course writes this default as `None`, which is fine as long as a system prompt is
# ALWAYS passed — the default never runs. Call it without one and `None` goes on the wire
# as a literal JSON null instead of the key being left out. `anthropic.omit` is the SDK's
# own sentinel for "not given", so both paths build a valid request.
def chat(client: anthropic.Anthropic, messages: list, system_prompt = anthropic.omit) -> str:

    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        system = system_prompt      # top-level parameter — NOT an entry in messages
    )

    return "".join(block.text for block in response.content if block.type == "text")


def main():

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()


    # Start with an empty message list
    messages = []

    # Constant for the whole session — but the API is stateless, so it is re-sent with
    # every single request, exactly like the message history is.
    system_prompt = """
        You are a patient math tutor.
        Do not directly answer a student's questions.
        Guide them to a solution step by step.
    """

    try:
        while True:

            user_input = input("> ")                                #inbuilt input function
            # print("> ",user_input)

            # a way out that isn't Ctrl+C
            if user_input.lower() in ("quit", "exit"):
                break

            # Add this turn's message to the history
            add_user_message(messages, user_input)
            
            # Get Claude's response — the system prompt goes up on every call
            answer = chat(client, messages, system_prompt)
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