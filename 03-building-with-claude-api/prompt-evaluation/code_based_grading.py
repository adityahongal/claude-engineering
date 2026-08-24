"""Code-based grading — syntax checks alongside the model grader.

Two graders working together: a code grader that parses the output (free, instant,
deterministic — no noise floor at all) and the model grader that judges whether the
answer actually addresses the task.

Two things this needs that the earlier files didn't:
  * the PROMPT must ask for code only. Parse a markdown answer full of headings and
    explanation and every syntax check fails on the prose, not the code.
  * each dataset row needs a "format" so the right validator runs.
"""

# Code grader

# When evaluating AI models that generate code, you need more than just checking if the response makes sense. 
# You also need to verify that the generated code actually has valid syntax and follows the correct format. 
# This is where code-based grading comes in.

# How Code Grading Works
# Code grading validates two key aspects of AI-generated responses:

# Format - The response should return only the requested code type (Python, JSON, or Regex) without explanations
# Valid Syntax - The generated code should actually parse correctly as the intended language
# Task Following - The response should directly address what was asked and be accurate

# The first two criteria are handled by the code grader, while task following is evaluated by the model grader. 
# Together, they provide a comprehensive evaluation.

import ast
import json
import os
import re
import sys
from pathlib import Path
from statistics import mean

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

# Sits next to this file, so Python finds it by module name — no path juggling.
from usage_tracker import UsageTracker

MODEL = "claude-sonnet-5"
GRADER_MODEL = "claude-haiku-4-5"
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

# `model` is a parameter now, not the constant — answering and grading use different ones.
def chat(client: anthropic.Anthropic, messages: list, model: str = MODEL,
         system = anthropic.omit, stop_sequences = anthropic.omit,
         tracker: UsageTracker | None = None) -> str:

    response = client.messages.create(
        model = model,
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
    # The code grader parses this output directly, so the prompt has to ask for code and
    # NOTHING else. Without these two lines Claude replies with a markdown document —
    # headings, explanation, fenced blocks — and every syntax check fails on the prose
    # rather than on the code.
    prompt = f"""
Please solve the following task:

{test_case["task"]}

Respond with only the {test_case["format"]} code. No explanation, no commentary,
no markdown code fences.
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
    
    # Grade the output
    model_grade = grade_by_model(client, test_case, output, tracker)
    model_score = model_grade["score"]
    reasoning = model_grade["reasoning"]

    # Free and instant — no API call, and the same input always gives the same answer.
    syntax_score = grade_syntax(output, test_case)

    # A GATE, not an average. Code that doesn't parse is worthless however good the idea
    # was, so it scores 0 rather than being averaged up to 5. Averaging a 1-10 judgement
    # with a binary 0/10 also distorts both ends: a syntax failure caps a strong answer at
    # 5, and a syntax pass drags a weak one up toward 10.
    score = model_score if syntax_score == 10 else 0

    # Both components are kept so a 0 is explainable — was the code invalid, or just poor?
    return {
        "output": output,
        "test_case": test_case,
        "score": score,
        "model_score": model_score,
        "syntax_score": syntax_score,
        "reasoning": reasoning
    }

# The run_eval Function
# This function coordinates the entire evaluation process:
def run_eval(client, dataset, tracker: UsageTracker | None = None) -> list[dict]:
    """Loads the dataset and calls run_test_case with each case"""
    results = []
    
    for test_case in dataset:
        result = run_test_case(client, test_case, tracker)
        results.append(result)

    # Finally, calculate an average score across all test cases:
    average_score = mean([result["score"] for result in results])
    print(f"Average score: {average_score}")
    
    return results

class Grade(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    reasoning: str
    score: int


# Implementing a Model Grader
def grade_by_model(client, test_case, output, tracker: UsageTracker | None = None) -> dict:
    
    eval_prompt = f"""
    You are an expert code reviewer. Evaluate this AI-generated solution.

    Task: {test_case["task"]}
    Solution: {output}

    Provide your evaluation as a structured JSON object with:
    - "strengths": An array of 1-3 key strengths
    - "weaknesses": An array of 1-3 key areas for improvement  
    - "reasoning": A concise explanation of your assessment
    - "score": A number between 1-10
    """
    
    messages = []
    add_user_message(messages, eval_prompt)

    response = client.messages.parse(
        model = GRADER_MODEL,
        max_tokens = MAX_TOKENS,
        messages = messages,
        output_format = Grade,
    )

    if tracker is not None:
        tracker.record(response)


    return response.parsed_output.model_dump()

# The key insight is asking for strengths, weaknesses, and reasoning alongside the score. 
# Without this context, models tend to default to middling scores around 6.

# Syntax Validation Functions
# To check if generated code has valid syntax, you can create three helper functions that attempt to parse the output:

# NO `client` here. These make no API call — they're pure local checks, so there's nothing
# to authenticate. `json.loads(client, text)` raises "loads() takes 1 positional argument".
# The rule was never "every function needs a client", only "every function that talks to
# the API does".

def validate_json(text: str) -> int:
    try:
        json.loads(text.strip())
        return 10
    except json.JSONDecodeError:
        return 0

def validate_python(text: str) -> int:
    try:
        ast.parse(text.strip())
        return 10
    except SyntaxError:
        return 0

def validate_regex(text: str) -> int:
    try:
        re.compile(text.strip())
        return 10
    except re.error:
        return 0


# Which validator to run depends on what the task asked for, which is why each row in
# dataset.json carries a "format".
VALIDATORS = {
    "json": validate_json,
    "python": validate_python,
    "regex": validate_regex,
}

def grade_syntax(output: str, test_case: dict) -> int:
    """0 or 10 — does the output parse as the format the task asked for?"""
    validator = VALIDATORS.get(test_case["format"])
    if validator is None:
        raise ValueError(f"No validator for format {test_case['format']!r}")
    return validator(output)

# Each function tries to parse the text as its respective format. 
# If parsing succeeds, it returns a perfect score of 10. 
# If it fails with an error, the syntax is invalid and returns 0.

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
