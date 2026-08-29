"""Structure with XML tags.

Tags separate the parts of a prompt that are instructions from the parts that are data, so
a long prompt stays unambiguous about which is which.
"""

# Custom Tag Names
# You don't need to use official XML tags. Create descriptive names that make sense for your content:

# <sales_records> is better than <data>
# <athlete_information> clearly identifies user details
# <my_code> and <docs> separate different types of content
# The more specific and descriptive your tag names, the better Claude can understand the purpose of each section.

# When to Use XML Tags
# XML tags are most useful when:

# Including large amounts of context or data
# Mixing different types of content (code, documentation, data)
# You want to be extra clear about content boundaries
# Working with complex prompts that interpolate multiple variables
# Even for shorter content, XML tags can help serve as delimiters that make your prompt structure more obvious to Claude.

from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent


def run_prompt(client, prompt_inputs, tracker):
    prompt = f"""
<task>
Generate a one-day meal plan for an athlete that meets their dietary restrictions.
</task>

<athlete_information>
    <goal>{prompt_inputs["goal"]}</goal>
    <height_cm>{prompt_inputs["height"]}</height_cm>
    <weight_kg>{prompt_inputs["weight"]}</weight_kg>
    <dietary_restrictions>{prompt_inputs["restrictions"]}</dietary_restrictions>
</athlete_information>

<output_guidelines>
    <guideline>Provide breakfast, lunch, dinner, and two snacks.</guideline>
    <guideline>For each meal, list the foods and exact portion sizes.</guideline>
    <guideline>Give a time of day for each meal.</guideline>
    <guideline>Include an estimated calorie count for each meal.</guideline>
    <guideline>Include the total estimated calories for the day.</guideline>
    <guideline>Include a macronutrient breakdown in grams: protein, carbohydrates, and fat.</guideline>
    <guideline>Keep the meal plan practical and easy to prepare.</guideline>
    <guideline>Do not include foods that violate the athlete's dietary restrictions.</guideline>
</output_guidelines>
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
