"""Generating an eval dataset with Claude.

Step 2 of the workflow: build the inputs a prompt will be scored against, rather than
hand-writing them.

The course gets JSON back with prefill + stop_sequences, which returns a 400 on
claude-sonnet-5. The live path here uses messages.parse() with a schema instead; the
course version is kept as a comment, since prefill is the course's default way of asking
for JSON and it recurs in later lessons.
"""

# Creating an Evaluation Dataset

# An evaluation dataset contains inputs that we'll feed into our prompt. '
# 'For each combination of prompt and input, we'll run the prompt and analyze the results.

# Our dataset will be an array of JSON objects, where each object contains a "task" property describing what we want Claude to accomplish.
# We can either create this dataset by hand or generate it automatically using Claude.

import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

MODEL = "claude-sonnet-5"
MAX_TOKENS = 1024

# helper functions
# add_assistant_message and chat are unused on the live path below — kept because the
# commented course version needs them.

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

# No temperature here: it 400s on claude-sonnet-5, and extra_body can't rescue a parameter
# the server rejects. stop_sequences is what the course's prefill route needs.
def chat(client: anthropic.Anthropic, messages: list, system = anthropic.omit,
         stop_sequences = anthropic.omit) -> str:

    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        system = system,
        stop_sequences = stop_sequences
    )

    return "".join(block.text for block in response.content if block.type == "text")


# The shape we want back. This replaces the "Example output" block the course puts in the
# prompt — with a schema attached, the schema IS the contract, so describing it in prose
# as well is redundant and can conflict with it.
class Task(BaseModel):
    task: str

class Dataset(BaseModel):
    tasks: list[Task]


# Now we'll create our dataset generation function:

def generate_dataset(client: anthropic.Anthropic) -> list[dict]:

    # Step 1 — the prompt describing what the dataset should contain
    prompt = """
Generate an evaluation dataset for a prompt evaluation. The dataset will be used to evaluate prompts that generate Python, JSON, or Regex specifically for AWS-related tasks. Generate an array of JSON objects, each representing task that requires Python, JSON, or a Regex to complete.

* Focus on tasks that can be solved by writing a single Python function, a single JSON object, or a single regex
* Focus on tasks that do not require writing much code

Please generate 3 objects.
"""

    # Step 2 — build the message list for THIS request. It belongs here, not in main():
    # the list is scratch state for one call, not something main needs to know about.
    messages = []
    add_user_message(messages, prompt)

    # Step 3 — one call, constrained to the schema. No fence to strip, no json.loads,
    # and a wrong shape can't come back.
    response = client.messages.parse(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        output_format = Dataset,
    )

    # Step 4 — parsed_output is already a validated Dataset. Convert the models back to
    # plain dicts so they can go straight to JSON.
    return [task.model_dump() for task in response.parsed_output.tasks]

    # --- the course's version, for reference ---------------------------------
    # Prefill + stop sequence. 400s on claude-sonnet-5 / opus-5 / 4.6-4.8; works on
    # claude-haiku-4-5. Note it needs json.loads() and trusts the text to be valid JSON.
    #
    #     messages = []
    #     add_user_message(messages, prompt)
    #     add_assistant_message(messages, "```json")   # prefill, not a stored reply
    #     text = chat(client, messages, stop_sequences=["```"])
    #     return json.loads(text)
    # -------------------------------------------------------------------------


def main():

    # Step 1 — .env into the environment BEFORE the client reads the key
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()

    try:
        # Step 2 — generate the dataset
        dataset = generate_dataset(client)
        print(dataset)

        # Step 3 — write it next to THIS file, not next to wherever python was launched
        out_path = Path(__file__).parent / "dataset.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        print("Saved →", out_path.name)

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
