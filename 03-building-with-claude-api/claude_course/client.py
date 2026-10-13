"""The client, and the error handling every lesson wraps around main()."""

import os
import sys

import anthropic
from dotenv import find_dotenv, load_dotenv

MODEL = "claude-sonnet-5"

# 8192, not 4096: measured in prompt-engineering/, where structured prompts made Claude
# write several times more and a 4096 ceiling cut answers off mid-sentence.
MAX_TOKENS = 8192


def get_client() -> anthropic.Anthropic:
    """Load .env, check the key is there, hand back a client.

    find_dotenv(usecwd=True) searches up from the directory the lesson is RUN from. Plain
    load_dotenv() searches up from the calling file — which, for code inside an installed
    package, is the package's own directory, not the lesson's.
    """
    load_dotenv(find_dotenv(usecwd=True))

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    return anthropic.Anthropic()


def run(main_fn) -> None:
    """Call main_fn() with the standard error handling around it: `run(main)`, no parentheses."""
    try:
        main_fn()
    except (KeyboardInterrupt, EOFError):
        print()
    except anthropic.AuthenticationError:
        sys.exit("Invalid API key.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited. Wait and retry.")
    except anthropic.APIStatusError as err:   # any other bad status: 400, 404, 5xx
        sys.exit(f"API error {err.status_code}: {err.message}")
    except anthropic.APIConnectionError:      # never reached the server
        sys.exit("Network error. Check your connection.")
