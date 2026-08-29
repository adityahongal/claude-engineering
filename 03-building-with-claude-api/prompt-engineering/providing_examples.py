"""Providing examples.

Showing a worked example instead of describing the output in prose. Usually the single
biggest lever of the four, and the easiest one to get subtly wrong.
"""

# When to Use Examples
# Examples are particularly useful for:

# Capturing corner cases or edge scenarios
# Defining complex output formats (like specific JSON structures)
# Showing the exact style or tone you want
# Demonstrating how to handle ambiguous inputs

# One-Shot vs Multi-Shot

# One-Shot: Provide a single example to establish the pattern
# Multi-Shot: Provide multiple examples to cover different scenarios

# Use multi-shot when you need to handle various edge cases or want to show different types of valid responses.

# One-shot teaches the format. Multi-shot can teach the format + variation.

# Note - below is the multi shot example and one shot example is actually used in code
# EXAMPLE_PLAN = """
# Example 1 — No dietary restrictions

# Input:
# - Goal: Build muscle
# - Height: 180 cm
# - Weight: 75 kg
# - Dietary restrictions: None

# Output:
# One-Day Meal Plan

# | Time | Meal | Foods | Portion | Calories |
# |------|------|-------|---------|----------|
# | 8:00 AM | Breakfast | Eggs, oatmeal, banana | 3 eggs, 80g oats, 1 banana | 600 |
# | 11:00 AM | Snack | Greek yogurt, almonds | 200g yogurt, 20g almonds | 250 |
# | 1:30 PM | Lunch | Chicken, rice, vegetables | 150g chicken, 200g rice, 150g vegetables | 650 |
# | 5:00 PM | Snack | Protein shake, banana | 1 serving, 1 banana | 300 |
# | 8:00 PM | Dinner | Chicken, potatoes, salad | 150g chicken, 250g potatoes, 100g salad | 600 |

# Total estimated calories: 2,400 kcal

# Macronutrients:
# - Protein: 165g
# - Carbohydrates: 260g
# - Fat: 70g


# Example 2 — Vegetarian athlete

# Input:
# - Goal: Maintain weight
# - Height: 165 cm
# - Weight: 60 kg
# - Dietary restrictions: Vegetarian

# Output:
# One-Day Meal Plan

# | Time | Meal | Foods | Portion | Calories |
# |------|------|-------|---------|----------|
# | 8:00 AM | Breakfast | Oatmeal, milk, berries | 60g oats, 250ml milk, 100g berries | 450 |
# | 11:00 AM | Snack | Greek yogurt, walnuts | 200g yogurt, 20g walnuts | 250 |
# | 1:30 PM | Lunch | Lentils, rice, vegetables | 200g lentils, 150g rice, 150g vegetables | 550 |
# | 5:00 PM | Snack | Peanut butter toast, banana | 2 slices toast, 20g peanut butter, 1 banana | 350 |
# | 8:00 PM | Dinner | Tofu, quinoa, vegetables | 150g tofu, 150g quinoa, 150g vegetables | 500 |

# Total estimated calories: 2,100 kcal

# Macronutrients:
# - Protein: 95g
# - Carbohydrates: 280g
# - Fat: 65g


# Example 3 — High-protein athlete

# Input:
# - Goal: Build muscle
# - Height: 175 cm
# - Weight: 80 kg
# - Dietary restrictions: None

# Output:
# One-Day Meal Plan

# | Time | Meal | Foods | Portion | Calories |
# |------|------|-------|---------|----------|
# | 7:30 AM | Breakfast | Eggs, whole-grain toast, fruit | 4 eggs, 2 slices toast, 1 apple | 550 |
# | 10:30 AM | Snack | Greek yogurt, berries | 250g yogurt, 100g berries | 250 |
# | 1:00 PM | Lunch | Chicken, brown rice, broccoli | 200g chicken, 200g rice, 150g broccoli | 700 |
# | 4:30 PM | Snack | Protein shake, banana | 1 serving, 1 banana | 300 |
# | 8:00 PM | Dinner | Salmon, potatoes, vegetables | 180g salmon, 250g potatoes, 150g vegetables | 650 |

# Total estimated calories: 2,450 kcal

# Macronutrients:
# - Protein: 190g
# - Carbohydrates: 240g
# - Fat: 80g
# """


#     prompt = f"""
# Generate a one-day meal plan for an athlete that meets their dietary restrictions.

# Athlete's goal: {prompt_inputs["goal"]}
# Athlete's height (cm): {prompt_inputs["height"]}
# Athlete's weight (kg): {prompt_inputs["weight"]}
# Dietary restrictions: {prompt_inputs["restrictions"]}

# Here are examples demonstrating the expected reasoning pattern and output format:

# {EXAMPLE_PLAN}

# Based on the athlete's information above:
# 1. Identify the athlete's goal and dietary restrictions.
# 2. Select appropriate foods that satisfy those restrictions.
# 3. Create breakfast, lunch, dinner, and two snacks.
# 4. Provide exact portion sizes and meal times.
# 5. Estimate calories and macronutrients.
# 6. Ensure no food violates the stated dietary restrictions.

# Follow the structure and level of detail shown in the examples, but create a new meal plan appropriate for the current athlete.
# """


from pathlib import Path

from helpers import ask, get_client, run
from prompt_engineering import DATASET, EXTRA_CRITERIA
from prompt_evaluator import PromptEvaluator

HERE = Path(__file__).parent

# The example lives outside run_prompt because it is fixed — the same worked meal plan is
# shown for every case, regardless of that case's inputs.
EXAMPLE_PLAN = """
Example:

Input:
- Goal: Build muscle
- Height: 180 cm
- Weight: 75 kg
- Dietary restrictions: None

Output:
One-Day Meal Plan

| Time | Meal | Foods | Portion | Calories |
|------|------|-------|---------|----------|
| 8:00 AM | Breakfast | Eggs, oatmeal, banana | 3 eggs, 80g oats, 1 banana | 600 |
| 11:00 AM | Snack | Greek yogurt, almonds | 200g yogurt, 20g almonds | 250 |
| 1:30 PM | Lunch | Grilled chicken, rice, vegetables | 150g chicken, 200g rice, 150g vegetables | 650 |
| 5:00 PM | Snack | Protein shake, banana | 1 serving, 1 banana | 300 |
| 8:00 PM | Dinner | Chicken, potatoes, salad | 150g chicken, 250g potatoes, 100g salad | 600 |

Total estimated calories: 2,400 kcal

Macronutrients:
- Protein: 165g
- Carbohydrates: 260g
- Fat: 70g
"""


def run_prompt(client, prompt_inputs, tracker):
    # The eight guidelines from being_specific.py are gone on purpose — the example
    # DEMONSTRATES all of them (times, exact portions, per-meal calories, a daily total, a
    # macro breakdown) instead of listing them. That is the whole trade this technique
    # makes: showing the shape rather than describing it.
    #
    # The three "Important" lines are the guard against the copying failure. The worked
    # example is a chicken-and-eggs plan for an athlete with no restrictions, and the
    # dataset contains a vegan case — without those lines, a plausible outcome is a
    # "vegan" plan with chicken in it, copied straight from the demonstration.
    prompt = f"""
Generate a one-day meal plan for an athlete that meets their dietary restrictions.

Athlete's goal: {prompt_inputs["goal"]}
Athlete's height (cm): {prompt_inputs["height"]}
Athlete's weight (kg): {prompt_inputs["weight"]}
Dietary restrictions: {prompt_inputs["restrictions"]}

Follow the structure and level of detail demonstrated in this example:

{EXAMPLE_PLAN}

Important:
- Adapt the meal plan to the athlete's actual goal and dietary restrictions.
- Do not blindly copy foods from the example.
- Do not include foods that violate the athlete's dietary restrictions.
- Follow the same output structure as the example.
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
