"""First call to the Claude API.

Same shape as any HTTP client: key from the environment, a request body, a
response to parse. The SDK builds the POST for you and hands back typed objects
instead of raw JSON.
"""

from __future__ import annotations

import os
import sys

import anthropic
from dotenv import load_dotenv

MODEL = "claude-haiku-4-5"  # cheapest tier — swap for claude-opus-5 when quality matters
MAX_TOKENS = 1024  # deliberately small to bound cost while learning


def ask(client: anthropic.Anthropic, prompt: str) -> str:
    """Send one prompt and return Claude's text reply."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    # content is a list of blocks, not a string. A block can be text, tool_use,
    # or thinking — so filter by type instead of grabbing content[0].
    return "".join(block.text for block in response.content if block.type == "text")


def main() -> None:
    load_dotenv()  # loads .env into the environment; the SDK reads it from there

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()

    try:
        print(ask(client, "In two sentences, what is a context window?"))
    except anthropic.AuthenticationError:
        sys.exit("Invalid API key.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited. Wait and retry.")
    except anthropic.APIStatusError as err:
        sys.exit(f"API error {err.status_code}: {err.message}")
    except anthropic.APIConnectionError:
        sys.exit("Network error. Check your connection.")


if __name__ == "__main__":
    main()
