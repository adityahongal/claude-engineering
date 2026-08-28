"""Being clear and direct.

Say plainly what you want done. Most weak prompts are not too short — they are ambiguous
about the task, the audience, or what a finished answer looks like.
"""

# Being Clear and Direct
# When crafting that crucial first line, you want to focus on two key principles: clarity and directness.
# This means using simple language that leaves no room for ambiguity about what you want Claude to do.

# 1.Clear Communication
# Being "clear" means:

# Use simple language that anyone can understand
# State exactly what you want without beating around the bush
# Lead with a straightforward statement of Claude's task
# Instead of writing something vague like "I need to know about those things people put on their roofs that use sun - those solar panel things, I think they're called,"
# be direct and write: "Write three paragraphs about how solar panels work."

# 2.Direct Instructions
# Being "direct" focuses on how you structure your request:

# Use instructions, not questions
# Start with direct action verbs like "Write," "Create," or "Generate"
# Rather than asking "I was reading about renewable energy and geothermal energy sounds neat. What countries use it?"
# try: "Identify three countries that use geothermal energy. Include generation stats for each."

# Putting It Into Practice
# Let's see this technique in action. Starting with a weak prompt that simply asked "What should this person eat?" we can apply our clear and direct approach.

# The improved version becomes: Generate a one-day meal plan for an athlete that meets their dietary restrictions.

# This revision immediately tells Claude:

# What action to take (generate)
# What to create (a meal plan)
# Key constraints (one day, for an athlete, meeting dietary restrictions)


# ─────────────────────────────────────────────────────────────────────────────────────
# Same dataset, same criteria, same grader — ONE thing different, the wording of the
# prompt. That is what makes the two scores comparable at all. Importing the config from
# prompt_engineering.py rather than re-typing it here is what keeps it honest: a stray edit
# to the criteria in one file would quietly turn the comparison into a measurement of two
# changes at once.
# ─────────────────────────────────────────────────────────────────────────────────────

from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent


def run_prompt(client, prompt_inputs, tracker):
    # Rewrite the naive "What should this person eat?" using the two principles above:
    # lead with an action verb, state the task plainly, name the constraints.
    #
    # The course's improved opening line is:
    #   "Generate a one-day meal plan for an athlete that meets their dietary restrictions."
    #
    # Keep the four inputs interpolated exactly as the baseline does — changing WHICH
    # information Claude gets would be a different experiment. Note the f prefix: without
    # it Claude receives the literal text {prompt_inputs["height"]}.
    # All four inputs the baseline receives, this one receives too. A wrong key raises
    # KeyError while the f-string is built — before any request goes out, so it costs
    # nothing. A MISSING key is the expensive mistake: it runs fine, returns a score, and
    # that score silently measures the wording change AND the lost information together.
    # Units in the labels because the values arrive as bare numbers.
    prompt = f"""
Generate a one-day meal plan for an athlete that meets their dietary restrictions.

Athlete's goal: {prompt_inputs["goal"]}
Athlete's height (cm): {prompt_inputs["height"]}
Athlete's weight (kg): {prompt_inputs["weight"]}
Dietary restrictions: {prompt_inputs["restrictions"]}
"""
    return ask(client, prompt, tracker=tracker)


def main():
    client = get_client()
    evaluator = PromptEvaluator(client, max_concurrent_tasks=3)

    evaluator.run_evaluation(
        run_prompt_function=run_prompt,
        dataset_file=str(DATASET),
        extra_criteria=EXTRA_CRITERIA,
        report_file=str(HERE / "report_clear_and_direct.html"),
    )

    # Compare against the baseline from prompt_engineering.py. A gain smaller than the
    # noise floor is not a gain — on three cases one grade moving by a point shifts the
    # average by 0.33, so treat anything under half a point as unproven.


if __name__ == "__main__":
    run(main)
