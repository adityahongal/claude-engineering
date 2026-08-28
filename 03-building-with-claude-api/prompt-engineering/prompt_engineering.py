"""Prompt engineering — the overview lesson.

What the techniques are for, and where they sit relative to evaluation: evaluation tells
you whether a prompt got better, prompt engineering is what you actually change. Module 3
built the measuring instrument; this module is the set of moves worth measuring.
"""

# Prompt engineering is about taking a prompt you've written and improving it to get more reliable, higher-quality outputs. 
# This process involves iterative refinement - starting with a basic prompt, evaluating its performance, 
# then systematically applying engineering techniques to improve it.

# The Iterative Improvement Process
# The approach follows a clear cycle that you can repeat until you achieve your desired results:

# 1.Set a goal - Define what you want your prompt to accomplish
# 2.Write an initial prompt - Create a basic first attempt
# 3.Evaluate the prompt - Test it against your criteria
# 4.Apply prompt engineering techniques - Use specific methods to improve performance
# 5.Re-evaluate - Verify that your changes actually improved the results

# You repeat the last two steps until you're satisfied with the performance. 
# Each iteration should show measurable improvement in your evaluation scores.

# To demonstrate this process, we'll work with a practical example: creating a prompt that generates one-day meal plans for athletes. 
# The prompt needs to take into account an athlete's height, weight, goals, and dietary restrictions, then produce a comprehensive meal plan.

# The evaluation setup uses a PromptEvaluator class that handles dataset generation and model grading. 
# When creating your evaluator instance, you can control concurrency with the max_concurrent_tasks parameter:

# evaluator = PromptEvaluator(max_concurrent_tasks=5)

# Start with a low concurrency value (like 3) to avoid rate limit errors. You can increase it if your API quota allows for faster processing.

# Generating Test Data
# The evaluation system can automatically generate test cases based on your prompt requirements. 
# You define what inputs your prompt needs:

# dataset = evaluator.generate_dataset(
#     task_description="Write a compact, concise 1 day meal plan for a single athlete",
#     prompt_inputs_spec={
#         "height": "Athlete's height in cm",
#         "weight": "Athlete's weight in kg", 
#         "goal": "Goal of the athlete",
#         "restrictions": "Dietary restrictions of the athlete"
#     },
#     output_file="dataset.json",
#     num_cases=3
# )

# Writing Your Initial Prompt
# Start with a simple, naive prompt to establish a baseline. 
# Here's an example of a deliberately basic first attempt:

# def run_prompt(prompt_inputs):
#     prompt = f"""
# What should this person eat?

# - Height: {prompt_inputs["height"]}
# - Weight: {prompt_inputs["weight"]}
# - Goal: {prompt_inputs["goal"]}
# - Dietary restrictions: {prompt_inputs["restrictions"]}
# """
    
#     messages = []
#     add_user_message(messages, prompt)
#     return chat(messages)
# This basic prompt will likely produce poor results, but it gives you a starting point to measure improvement against.


# Adding Evaluation Criteria
# When running your evaluation, you can specify additional criteria that the grading model should consider:

# results = evaluator.run_evaluation(
#     run_prompt_function=run_prompt,
#     dataset_file="dataset.json",
#     extra_criteria="""
# The output should include:
# - Daily caloric total
# - Macronutrient breakdown  
# - Meals with exact foods, portions, and timing
# """
# )
# This helps ensure your prompt is evaluated against the specific requirements that matter for your use case.

# Analyzing Results
# After running an evaluation, you'll get both a numerical score and a detailed HTML report.
# The report shows you exactly how each test case performed, including the model's reasoning for each score.


# ─────────────────────────────────────────────────────────────────────────────────────
# The baseline.
#
# The naive prompt below is meant to be weak. Its score is not a result, it is the number
# every later lesson gets measured against — so it is worth running once and leaving alone.
#
#   dataset.json   the fixed inputs, generated once and committed
#        ↓
#   run_prompt     wraps those inputs in a template  ← the only thing that changes
#        ↓
#   the evaluator  answers, grades, averages
#        ↓
#   a score        comparable across lessons because everything else held still
# ─────────────────────────────────────────────────────────────────────────────────────

import json
from pathlib import Path

from helpers import ask, get_client, run
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent
DATASET = HERE / "dataset.json"

TASK_DESCRIPTION = "Write a compact, concise 1 day meal plan for a single athlete"

# What each generated case has to supply. The descriptions go into the schema, so Claude
# knows `height` means centimetres without being told again in prose.
PROMPT_INPUTS_SPEC = {
    "height": "Athlete's height in cm",
    "weight": "Athlete's weight in kg",
    "goal": "Goal of the athlete",
    "restrictions": "Dietary restrictions of the athlete",
}

# Requirements applied to EVERY case, on top of each case's own solution_criteria. This is
# where you state what a good answer contains — leave it vague and the grader invents its
# own standard, differently each run.
EXTRA_CRITERIA = """
- A daily caloric total
- A macronutrient breakdown
- Meals with exact foods, portions, and timing
"""


# The deliberately naive first attempt, straight from the course. Three arguments in, a
# string out — `client` and `tracker` are handed over by the evaluator rather than picked
# up from a global, because a script has no shared namespace the way a notebook does.
def run_prompt(client, prompt_inputs, tracker):
    prompt = f"""
What should this person eat?

- Height: {prompt_inputs["height"]}
- Weight: {prompt_inputs["weight"]}
- Goal: {prompt_inputs["goal"]}
- Dietary restrictions: {prompt_inputs["restrictions"]}
"""
    return ask(client, prompt, tracker=tracker)


def main():
    client = get_client()
    evaluator = PromptEvaluator(client, max_concurrent_tasks=3)

    # Generate ONCE. An eval set that changes underneath you is not a baseline — regenerate
    # it and every score from every previous lesson becomes incomparable. Delete the file
    # deliberately if you ever really want a new one.
    if not DATASET.exists():
        evaluator.generate_dataset(
            task_description=TASK_DESCRIPTION,
            prompt_inputs_spec=PROMPT_INPUTS_SPEC,
            output_file=str(DATASET),
            # Ten, not three. Generating cases costs a few cents once; on three cases a
            # single grade moving one point swings the average by 0.33, which is larger
            # than most of the improvements this module is trying to detect. Run a subset
            # with limit= while drafting, and the full ten when a number has to mean
            # something.
            num_cases=10,
        )
    else:
        # Print the real count. num_cases above only applies when the file does not exist,
        # so raising it does nothing on its own — the committed dataset is what runs.
        existing = json.loads(DATASET.read_text(encoding="utf-8"))
        print(f"Using existing {DATASET.name} — {len(existing)} cases. "
              f"Delete it to regenerate at num_cases.")

    evaluator.run_evaluation(
        run_prompt_function=run_prompt,   # no parentheses: passing the function itself
        dataset_file=str(DATASET),
        extra_criteria=EXTRA_CRITERIA,
        report_file=str(HERE / "report_baseline.html"),
    )


if __name__ == "__main__":
    run(main)