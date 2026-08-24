"""Model-based grading — a second Claude call scores each answer.

Completes the loop: answer every task, then judge each answer against a rubric and average
the scores. That average is the number a prompt change is measured by.

Two models, two roles — MODEL answers (the thing being evaluated, must stay fixed across
runs), GRADER_MODEL judges (simpler job, cheaper, and the only one where prefill still
works).
"""

# Model Based Grading

# When building prompt evaluation workflows, grading systems provide objective signals about output quality. 
# A grader takes model output and returns some kind of measurable feedback - typically a number between 1 and 10, 
# where 10 represents high quality and 1 represents poor quality.

# There are three main approaches to grading model outputs:

# Code graders - Programmatically evaluate outputs using custom logic
# Model graders - Use another AI model to assess the quality
# Human graders - Have people manually review and score outputs

# Code Graders
# Code graders let you implement any programmatic check you can imagine. Common uses include:
# Checking output length
# Verifying output does/doesn't have certain words
# Syntax validation for JSON, Python, or regex
# Readability scores
# The only requirement is that your code returns some usable signal - usually a number between 1 and 10.

# Model Graders
# Model graders feed your original output into another API call for evaluation. This approach offers tremendous flexibility for assessing:
# Response quality
# Quality of instruction following
# Completeness
# Helpfulness
# Safety

# Human Graders
# Human graders provide the most flexibility but are time-consuming and tedious. They're useful for evaluating:
# General response quality
# Comprehensiveness
# Depth
# Conciseness
# Relevance

# Defining Evaluation Criteria

# Before implementing any grader, you need clear evaluation criteria. For a code generation prompt, you might focus on:
# Format - Should return only Python, JSON, or Regex without explanation
# Valid Syntax - Produced code should have valid syntax
# Task Following - Response should directly address the user's task with accurate code

# The first two criteria work well with code graders, 
# while task following is better suited for model graders due to their flexibility.

import json
import os
import sys
from pathlib import Path
from statistics import mean

import anthropic
from dotenv import load_dotenv
from pydantic import BaseModel

# Sits next to this file, so Python finds it by module name — no path juggling.
from usage_tracker import UsageTracker

# Two models, two roles. MODEL answers the tasks — that's the thing being evaluated, so it
# must stay the same across runs or scores aren't comparable. GRADER_MODEL judges the
# answers: a simpler job, and about a third the cost.
#
# The grader must stay on Haiku while it uses prefill: `add_assistant_message(..., "```json")`
# is accepted there and 400s on claude-sonnet-5.
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
    
    # Grade the output
    model_grade = grade_by_model(client, test_case, output, tracker)
    score = model_grade["score"]
    reasoning = model_grade["reasoning"]
    
    return {
        "output": output,
        "test_case": test_case,
        "score": score,
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

# Each result contains three key pieces of information:

# output: The complete response from Claude
# test_case: The original test case that was processed
# score: The evaluation score

# The shape a grade must come back in. Asking for JSON in prose and calling json.loads()
# on the reply works most of the time — and fails intermittently, which is worse than
# failing always. Two ways it breaks with this dataset:
#   * the reasoning quotes regex, and one mis-escaped backslash kills the parse
#   * the reasoning quotes code in a fenced block, and stop_sequences=["```"] then cuts
#     generation off mid-JSON
# A schema removes both: generation is constrained, so malformed JSON can't be produced.
# `score: int` also pins the scale — the prose version returned 6, 7.5 and 8 across three
# calls, which makes a shaky baseline.
class Grade(BaseModel):
    strengths: list[str]
    weaknesses: list[str]
    reasoning: str
    score: int


# Implementing a Model Grader
def grade_by_model(client, test_case, output, tracker: UsageTracker | None = None) -> dict:
    # Create evaluation prompt
    # NOTE THE f. Without it, {task} and {solution} stay as literal text and the grader
    # reviews the placeholders instead of the answer — and still returns a plausible
    # score, so the average looks fine and means nothing.
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

    # A validated Grade, not text. No fence to strip, no json.loads, no way to get
    # malformed JSON back.
    return response.parsed_output.model_dump()

    # --- the course's version, for reference ---------------------------------
    # Prefill + stop sequence, then parse the text. Works on claude-haiku-4-5 (prefill
    # 400s on sonnet-5), but raises JSONDecodeError intermittently — see the note above.
    #
    #     add_assistant_message(messages, "```json")
    #     eval_text = chat(client, messages, model=GRADER_MODEL,
    #                      stop_sequences=["```"], tracker=tracker)
    #     return json.loads(eval_text)
    # -------------------------------------------------------------------------

# The key insight is asking for strengths, weaknesses, and reasoning alongside the score. 
# Without this context, models tend to default to middling scores around 6.

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
