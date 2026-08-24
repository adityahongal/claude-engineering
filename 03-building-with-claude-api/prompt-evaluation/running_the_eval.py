"""Running the eval — every task in the dataset through the prompt, answers collected.

Reads dataset.json, merges each task into the prompt template, calls Claude once per task,
and writes the answers to answers.json so grading can run later without paying to answer
everything again.

Three layers, each one step more specific:

    run_eval          for every task in the dataset...
      run_test_case     ...answer it and score it...
        run_prompt        ...by filling the template and calling Claude

`client` is threaded through all three. In the course's notebook it's a global every cell
can see; in a script it has to be passed.
"""

# Running the Eval

# Now that we have our evaluation dataset ready, it's time to build the core evaluation pipeline. 
# This involves taking each test case, merging it with our prompt, feeding it to Claude, and then grading the results.

# The evaluation process follows a clear workflow: we take our dataset of test cases, combine each one with our prompt template, 
# send it to Claude for processing, and then evaluate the output using a grader system.

import json
import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

# Sits next to this file, so Python finds it by module name — no path juggling.
from usage_tracker import UsageTracker

MODEL = "claude-sonnet-5"
# 1024 truncated two of the three answers — these tasks want a regex plus explanation, a
# Python function, a full IAM policy. Code and JSON tokenize denser than prose, so char
# count is a poor guide. The tracker now warns when anything hits the ceiling.
MAX_TOKENS = 4096

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

# No temperature here: it 400s on claude-sonnet-5, and extra_body can't rescue a parameter
# the server rejects. stop_sequences is what the course's prefill route needs.
# `tracker` is optional so chat() still works without one.
def chat(client: anthropic.Anthropic, messages: list, system = anthropic.omit,
         stop_sequences = anthropic.omit, tracker: UsageTracker | None = None) -> str:

    response = client.messages.create(
        model = MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        system = system,
        stop_sequences = stop_sequences
    )

    if tracker is not None:
        tracker.record(response)

    return "".join(block.text for block in response.content if block.type == "text")

# The evaluation process follows a clear workflow: 
# we take our dataset of test cases, combine each one with our prompt template, send it to Claude for processing, 
# and then evaluate the output using a grader system.

# The run_prompt Function
# This function takes a test case and merges it with our prompt template:
def run_prompt(client, test_case, tracker: UsageTracker | None = None) -> str:
    """Merges the prompt and test case input, then returns the result"""
    prompt = f"""
Please solve the following task:

{test_case["task"]}
"""
    messages = []
    add_user_message(messages,prompt)

    output = chat(client, messages, tracker=tracker)

    return output

# The run_test_case Function
# This function orchestrates running a single test case and grading the result:
def run_test_case(client, test_case, tracker: UsageTracker | None = None) -> dict:
    """Calls run_prompt, then grades the result"""
    output = run_prompt(client, test_case, tracker)
    
    # TODO - Grading - hardcoded for now
    score = 10
    
    return {
        "output": output,
        "test_case": test_case,
        "score": score
    }

# The run_eval Function
# This function coordinates the entire evaluation process:
def run_eval(client, dataset, tracker: UsageTracker | None = None) -> list[dict]:
    """Loads the dataset and calls run_test_case with each case"""
    results = []
    
    for test_case in dataset:
        result = run_test_case(client, test_case, tracker)
        results.append(result)
    
    return results

# Each result contains three key pieces of information:

# output: The complete response from Claude
# test_case: The original test case that was processed
# score: The evaluation score (currently hardcoded)

def main():

    # Step 1 — .env into the environment BEFORE the client reads the key
    load_dotenv()

    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

    client = anthropic.Anthropic()
    tracker = UsageTracker(MODEL)

    here = Path(__file__).parent

    try:

        # Running the Evaluation
        # To execute our evaluation pipeline, we load our dataset and run it through our functions:

        # READ the committed dataset 
        with open(here / "dataset.json", encoding="utf-8") as f:
            dataset = json.load(f)

        results = run_eval(client, dataset, tracker)

        # storing in answer.json to use it for grading later
        # Answering is the expensive half; grading is what gets iterated on. Saving the
        # answers means grading can re-run without paying to answer again.
        out_path = here / "answers.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

        print(json.dumps(results, indent=2))
        print("Saved →", out_path.name)
        tracker.report()

    except FileNotFoundError:
        sys.exit("dataset.json not found. Run generating_test_datasets.py first.")
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
