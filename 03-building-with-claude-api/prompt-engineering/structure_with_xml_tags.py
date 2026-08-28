"""Structure with XML tags.

Tags separate the parts of a prompt that are instructions from the parts that are data, so
a long prompt stays unambiguous about which is which.
"""

from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent


def run_prompt(client, prompt_inputs, tracker):
    # The athlete's details are DATA; the meal-plan instructions are INSTRUCTIONS. By this
    # point the prompt is long enough that the boundary between the two has gone fuzzy —
    # tags such as <athlete>...</athlete> put it back.
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
        report_file=str(HERE / "report_xml_tags.html"),
    )


if __name__ == "__main__":
    run(main)
