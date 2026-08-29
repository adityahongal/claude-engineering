"""Being specific.

Constraints the answer has to satisfy — format, length, what to leave out, what to do at
the edges. Vague instructions leave Claude to pick, and it will pick differently each run.
"""

# When working with Claude, one of the most effective ways to improve your results is to be specific about what you want.
# Instead of leaving everything up to the model's interpretation,
# you can provide clear guidelines or steps that direct Claude toward the kind of output you're looking for.

# Think about it this way: if you ask Claude to "write a short story about a character who discovers a hidden talent,"
# Claude could go in countless directions. The story might be 200 words or 2,000 words.
# It might have one character or five. It could focus on any type of talent discovery scenario.

# Two Types of Guidelines
# There are two main approaches to being specific in your prompts

# 1. Output Quality Guidelines
# The first type focuses on listing qualities that your output should have.
# These guidelines help you control:

# Length of the response
# Structure and format
# Specific attributes or elements to include
# Tone or style requirements
# For example, you might specify that a story should be under 1,000 words,
# include a clear action that reveals the character's talent, and feature at least one supporting character.

# 2. Process Steps
# The second type provides specific steps for Claude to follow.
# This approach is particularly useful when you want Claude to think through a problem systematically
# or consider multiple perspectives before arriving at a final answer.

# Instead of jumping straight to writing, you might ask Claude to:

# Brainstorm three talents that would create dramatic tension
# Pick the most interesting talent
# Outline a pivotal scene that reveals the talent
# Brainstorm supporting character types that could increase the impact

# When to Use Each Approach ??

# Always Use Output Guidelines
# You should include quality guidelines in almost every prompt you write.
# They're your safety net for getting consistent, useful results.

# Use Process Steps For Complex Problems
# Add step-by-step instructions when you're dealing with:

# Troubleshooting complex problems
# Decision-making scenarios
# Critical thinking tasks
# Any situation where you want Claude to consider multiple angles

# In professional prompting, you'll often see both techniques used together.
# You might have guidelines that control the format and content of your output,
# plus steps that ensure Claude thinks through the problem thoroughly before responding.

# 1. Specificity through output guidelines

# prompt = f"""
# Generate a one-day meal plan for an athlete that meets their dietary restrictions.

# Athlete's goal: {prompt_inputs["goal"]}
# Athlete's height (cm): {prompt_inputs["height"]}
# Athlete's weight (kg): {prompt_inputs["weight"]}
# Dietary restrictions: {prompt_inputs["restrictions"]}

# Output guidelines:
# - Provide breakfast, lunch, dinner, and two snacks.
# - For each meal, list the foods and approximate portion sizes.
# - Include an estimated calorie count for each meal.
# - Include the total estimated calories for the day.
# - Keep the meal plan practical and easy to prepare.
# - Do not include foods that violate the athlete's dietary restrictions.
# """

# 2. Specificity through process steps

# prompt = f"""
# Generate a one-day meal plan for an athlete that meets their dietary restrictions.

# Athlete's goal: {prompt_inputs["goal"]}
# Athlete's height (cm): {prompt_inputs["height"]}
# Athlete's weight (kg): {prompt_inputs["weight"]}
# Dietary restrictions: {prompt_inputs["restrictions"]}

# Follow these steps:
# 1. Review the athlete's height, weight, dietary restrictions, and food preferences.
# 2. Identify foods and meal options that are compatible with the dietary restrictions.
# 3. Plan breakfast, lunch, dinner, and two snacks.
# 4. Choose reasonable portion sizes for each meal.
# 5. Estimate the calories for each meal.
# 6. Check the complete plan to ensure no dietary restriction has been violated.
# 7. Present the final meal plan in a clear table.

# Output guidelines:
# - Include meal name, foods, portion sizes, and estimated calories.
# - Include the estimated daily calorie total.
# - Keep the plan practical and easy to prepare.
# """

from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent


def run_prompt(client, prompt_inputs, tracker):
    # Build on the clear-and-direct version rather than starting over, and add ONE kind of
    # constraint — the techniques stack, and stacking them one at a time is what tells you
    # which one earned the score.
    # Guidelines are only worth what they cover. The grader scores against EXTRA_CRITERIA —
    # daily calories, a macronutrient breakdown, and meals with exact foods, portions and
    # timing — so every one of those needs naming here. Being specific about things nobody
    # measures adds cost and no score, while leaving a graded item unstated leaves it to
    # chance. "exact", not "approximate", for the same reason: asking for the weaker
    # version of what is being graded is a guaranteed way to lose points.
    prompt = f"""
Generate a one-day meal plan for an athlete that meets their dietary restrictions.

Athlete's goal: {prompt_inputs["goal"]}
Athlete's height (cm): {prompt_inputs["height"]}
Athlete's weight (kg): {prompt_inputs["weight"]}
Dietary restrictions: {prompt_inputs["restrictions"]}

Output guidelines:
- Provide breakfast, lunch, dinner, and two snacks.
- For each meal, list the foods and exact portion sizes.
- Give a time of day for each meal.
- Include an estimated calorie count for each meal.
- Include the total estimated calories for the day.
- Include a macronutrient breakdown in grams: protein, carbohydrates, and fat.
- Keep the meal plan practical and easy to prepare.
- Do not include foods that violate the athlete's dietary restrictions.
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
