"""Temperature — the same prompt run repeatedly at two settings.

Not a chat loop: a loop hides the effect, because you never see the same prompt
answered twice. Six one-shot calls make the contrast obvious instead.

Two things have changed since this lesson was recorded:
  * the Python SDK (1.0.0) REMOVED `temperature` from messages.create() — passing it
    raises TypeError locally, before any request is sent. `extra_body` is the escape
    hatch that still puts it in the JSON body.
  * current frontier models (claude-sonnet-5, claude-opus-5, the 4.7/4.8 family) reject
    it server-side with a 400. claude-haiku-4-5 still accepts it, which is why this one
    file uses Haiku while everything else in the folder uses Sonnet.

The concept is still worth knowing — temperature is everywhere in the OpenAI, Gemini
and LangChain APIs. It is simply no longer how you steer Claude; prompting is.
"""

# Temperature

# Temperature is a powerful parameter that controls how predictable or creative Claude's responses will be.

# How Claude Generates Text
# When you send Claude a prompt like "What do you think?", it goes through three key steps:

# Tokenization - Breaking your input into smaller chunks
# Prediction - Calculating probabilities for possible next words
# Sampling - Choosing a token based on those probabilities

# Temperature is a decimal value between 0 and 1 that directly influences these selection probabilities. 
# It's like adjusting the "creativity dial" on Claude's responses.

# At low temperatures (near 0), Claude becomes very deterministic - it almost always picks the highest probability token. 
# At high temperatures (near 1), Claude distributes probability more evenly across options, leading to more varied and creative outputs.

# Choosing the Right Temperature
# Different tasks call for different temperature ranges:

# Low Temperature (0.0 - 0.3)

# Factual responses
# Coding assistance
# Data extraction
# Content moderation

# Medium Temperature (0.4 - 0.7)

# Summarization
# Educational content
# Problem-solving
# Creative writing with constraints

# High Temperature (0.8 - 1.0)

# Brainstorming
# Creative writing
# Marketing content
# Joke generation

# Remember that temperature doesn't guarantee different outputs - it just changes the probability of getting them. 
# Even at high temperatures, Claude might occasionally produce similar responses. 
# The key is matching your temperature choice to your specific use case:

# Need consistent, factual responses? Use low temperature
# Want creative brainstorming? Dial up the temperature
# Somewhere in between? Medium temperatures work well for most general tasks

import os
import sys

import anthropic
from dotenv import load_dotenv

MODEL = "claude-haiku-4-5"                              # works only on haiku model
MAX_TOKENS = 1024

# helper functions

def add_user_message(messages, prompt):
    user_message = {
        "role" : "user",
        "content" : prompt
    }

    messages.append(user_message)

# No add_assistant_message in this file — every call below is a fresh one-shot request,
# so there is no conversation to append a reply to.

def chat(client: anthropic.Anthropic, messages: list, temperature = 1.0) -> str:                    #added temperature

    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        extra_body = {"temperature": temperature},    # SDK dropped the typed parameter
    )

    return "".join(block.text for block in response.content if block.type == "text")


# A prompt with room to vary. A factual question ("what is 2+2") reads the same at every
# temperature, so it would prove nothing.
PROMPT = "Write a one-sentence opening line for a story about a lighthouse."
RUNS = 3


def run_at(client: anthropic.Anthropic, temperature: float, runs: int = RUNS) -> None:
    """Send the same prompt `runs` times at one temperature setting."""
    print(f"\ntemperature = {temperature}")
    print("-" * 50)

    for n in range(1, runs + 1):
        # A FRESH list every run. Reuse one and the earlier answers sit in the history,
        # so Claude is deliberately avoiding what it already said — variation that looks
        # like temperature but isn't.
        messages = []
        add_user_message(messages, PROMPT)
        print(f"{n}. {chat(client, messages, temperature)}")


def main():

    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()


    try:
        # Same prompt, same model, both ends of the dial.
        run_at(client, 0.0)   # near-deterministic — expect three near-identical lines
        run_at(client, 1.0)   # varied — expect three noticeably different lines

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