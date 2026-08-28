"""Being specific.

Constraints the answer has to satisfy — format, length, what to leave out, what to do at
the edges. Vague instructions leave Claude to pick, and it will pick differently each run.
"""

from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent


def run_prompt(client, prompt_inputs, tracker):
    # Build on the clear-and-direct version rather than starting over, and add ONE kind of
    # constraint — the techniques stack, and stacking them one at a time is what tells you
    # which one earned the score.
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
        report_file=str(HERE / "report_specific.html"),
    )


if __name__ == "__main__":
    run(main)
