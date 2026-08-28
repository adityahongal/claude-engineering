"""Providing examples.

Showing a worked example instead of describing the output in prose. Usually the single
biggest lever of the four, and the easiest one to get subtly wrong.
"""

from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent

# The example lives outside run_prompt because it is fixed — the same worked meal plan is
# shown for every case, regardless of that case's inputs.
EXAMPLE_PLAN = """
"""


def run_prompt(client, prompt_inputs, tracker):
    # Claude copies whatever the example demonstrates, including things you did not mean to
    # demonstrate. If the example plan is built around chicken, expect chicken back for the
    # vegetarian case — which is exactly the kind of failure the awkward test case exists
    # to catch.
    prompt = f"""
"""
    return ask(client, prompt, tracker=tracker)


def main():
    client = get_client()
    evaluator = PromptEvaluator(client, max_concurrent_tasks=3)

    evaluator.run_evaluation(
        run_prompt_function=run_prompt,
        dataset_file=str(DATASET),
        extra_criteria=EXTRA_CRITERIA,
        report_file=str(HERE / "report_examples.html"),
    )


if __name__ == "__main__":
    run(main)
