"""Sending a request to the Messages API.

The three required parameters of client.messages.create(), pulling the text out of
the response blocks, and handling the errors that can come back instead.
"""

# from dotenv import load_dotenv        #Imports a function that loads environment variables from a .env file.

# load_dotenv()                         #loads the .env key/value pairs into Python's environment.

# from anthropic import Anthropic

# client = Anthropic()
# model = "claude-sonnet-4-0"           # what the course videos use — deprecated, use claude-sonnet-5
# max_tokens = 1024

# The Create Function

# The core of making API requests is the client.messages.create() function. This function requires three key parameters:
# model - The name of the Claude model you want to use
# max_tokens - A safety limit on response length (not a target)
# messages - The conversation history you're sending to Claude

# The max_tokens parameter acts as a safety mechanism. If you set it to 1000, Claude will stop generating after 1000 tokens even if it has more to say. 
# Claude doesn't try to reach this limit - it just writes what it thinks is appropriate and stops if it hits the maximum.

# Understanding Messages

# Messages represent the conversation between you and Claude, similar to a chat application. There are two types of messages:
# User messages - Content you want to send to Claude (written by humans)
# Assistant messages - Responses that Claude has generated
# Each message is a dictionary with a role (either "user" or "assistant") and content (the actual text).
# Worth knowing: there is no "system" role in this list. In the Anthropic API the system prompt
# is a separate top-level parameter on create() — unlike OpenAI, where system IS a message role.

# making first request 
# message = client.messages.create(
#     model=model,
#     max_tokens=max_tokens,
#     messages=[
#         {
#             "role" : "user",
#             "content" : "what is quantam computing ? Answer in a line"
#         }
#     ]
# )

# extracting the response
# print(message.content[0].text)

# written nicely below

# Two ways to import. Both are valid Python:
#
#   from anthropic import Anthropic   -> binds ONLY the class   (JS: import { Anthropic } from "...")
#   import anthropic                  -> binds the WHOLE module (JS: import * as anthropic from "...")
#
# The course uses the first. This file uses the second, because the exception classes
# (AuthenticationError, APIStatusError, ...) live on the MODULE, not on the class.
# So `Anthropic.AuthenticationError` does NOT exist — `anthropic.AuthenticationError` does.
#
# Watch the capitalisation: `anthropic` is the module, `Anthropic` is the client class inside it.

import os  # read environment variables            (JS: process.env)
import sys  # sys.exit(msg) — stop with a message   (JS: process.exit(1))

import anthropic
from dotenv import load_dotenv

MODEL = "claude-sonnet-5"   # exact string from the docs — never build an ID by analogy
MAX_TOKENS = 1024           # a ceiling on the response length, not a target

def ask(client: anthropic.Anthropic, prompt: str) -> str:

    # send prompt to claude and receive response
    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = [
            { "role": "user",
                "content" : prompt      # the variable — no quotes, or it'd be a literal string
             }
        ]
    )

    # response.content is a LIST of blocks, not a string.
    # A block's .type is "text", or "tool_use" (Claude asking to run a tool), or "thinking".
    # Only text blocks have a .text attribute — the others raise AttributeError.
    # So: keep the text blocks, take each .text, glue them into one string.
    # This is the comprehension form of:
    #     parts = []
    #     for block in response.content:
    #         if block.type == "text":
    #             parts.append(block.text)
    #     return "".join(parts)
    return "".join(block.text for block in response.content if block.type == "text")

def main():

    # ORDER MATTERS. load_dotenv() copies .env into the environment, and the client reads
    # the key ONCE, at construction. Build the client before this line and it captures
    # None forever — no later load_dotenv() can repair it.
    load_dotenv()

    # Guard clause: fail immediately with a useful message instead of dying deep inside
    # the SDK. `not` catches a missing key (None) and an empty one ("") in one check.
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    # Built here, after the key exists — which also means importing this file never
    # creates a client as a side effect.
    client = anthropic.Anthropic()

    # except clauses are checked top to bottom, first match wins (like if/elif).
    # AuthenticationError and RateLimitError are SUBCLASSES of APIStatusError, so they
    # must come above it — put the parent first and it would swallow both.
    try:
        print(ask(client, "What is quantum computing?"))
    except anthropic.AuthenticationError:
        sys.exit("Invalid API key.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited. Wait and retry.")
    except anthropic.APIStatusError as err:   # any other bad status: 400, 404, 5xx
        sys.exit(f"API error {err.status_code}: {err.message}")
    except anthropic.APIConnectionError:      # never reached the server (network/DNS/timeout)
        sys.exit("Network error. Check your connection.")

if __name__ == "__main__" :
    main()