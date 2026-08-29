"""The evaluation harness the course hands you as `PromptEvaluator`.

Nothing here is new — it is the pipeline built by hand in ../prompt-evaluation/ (run the
prompt, grade the answer, average the scores) packaged as a class so a lesson can be three
lines instead of eighty. Worth reading rather than treating as a black box: everything in
it was written from scratch two folders ago.

What changed from module 3, and why the old dataset doesn't fit here:

  module 3   a row was a whole task string      -> the prompt WAS the thing under test
  module 4   a row is a dict of prompt_inputs   -> the prompt is a TEMPLATE around them

That is the entire point of the module. The inputs stay fixed while the template around
them gets rewritten, so any score change is attributable to the wording and nothing else.

One deliberate difference from the course version. In the notebook, `run_prompt` takes only
`prompt_inputs` and reaches out to a global `client`. Scripts have no shared namespace, so
here the evaluator passes what the function needs:

    def run_prompt(client, prompt_inputs, tracker):
        prompt = f"...{prompt_inputs['height']}..."
        return ask(client, prompt, tracker=tracker)

Three arguments in, a string out. Same shape as every other function in this repo.
"""

import html
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import mean

from pydantic import BaseModel, Field, create_model

from helpers import UsageTracker, add_user_message

ANSWER_MODEL = "claude-sonnet-5"
GRADER_MODEL = "claude-haiku-4-5"
MAX_TOKENS = 4096


class Grade(BaseModel):
    """What the grader has to fill in.

    Asking for strengths, weaknesses and reasoning BEFORE the score is not decoration — a
    grader made to justify itself first spreads its scores out. Ask for a bare number and
    almost everything comes back a 6.
    """
    strengths: list[str]
    weaknesses: list[str]
    reasoning: str
    score: int


class PromptEvaluator:
    """Generate a dataset, run a prompt against it, grade the results, report a score."""

    def __init__(self, client, max_concurrent_tasks: int = 3,
                 answer_model: str = ANSWER_MODEL, grader_model: str = GRADER_MODEL):
        self.client = client
        self.max_concurrent_tasks = max_concurrent_tasks
        self.answer_model = answer_model
        self.grader_model = grader_model

        # Two trackers, because the two roles run on different models at different prices.
        # A single total would hide that grading is the cheap half.
        self.answer_tracker = UsageTracker(answer_model)
        self.grader_tracker = UsageTracker(grader_model)

        # Test cases run on several threads at once, and `tracker.record()` does `+=` on a
        # counter. That is a read-then-write, so two threads can interleave and lose a
        # count. The lock makes recording one indivisible step.
        self._lock = threading.Lock()

    # ── step 2 of the workflow: build the dataset ────────────────────────────────────

    def generate_dataset(self, task_description: str, prompt_inputs_spec: dict[str, str],
                         output_file: str, num_cases: int = 3) -> list[dict]:
        """Ask Claude for test cases, validate them against a schema, write them to disk.

        `prompt_inputs_spec` is {field_name: what_that_field_means}. The field names are
        not known until you call this, so the schema has to be built at runtime —
        `create_model` is the Pydantic equivalent of writing a class by hand:

            create_model("PromptInputs", height=(str, ...), weight=(str, ...))

        is the same thing as

            class PromptInputs(BaseModel):
                height: str
                weight: str

        only assembled from a dict instead of typed out, because the dict is the argument.
        """
        # The description of each field goes INTO the schema, so Claude sees "Athlete's
        # height in cm" rather than just the bare name `height`.
        fields = {
            name: (str, Field(description=description))
            for name, description in prompt_inputs_spec.items()
        }
        PromptInputs = create_model("PromptInputs", **fields)

        TestCase = create_model(
            "TestCase",
            prompt_inputs=(PromptInputs, ...),
            solution_criteria=(
                list[str],
                Field(description="3-5 specific, checkable things a good answer must do "
                                  "for THIS case. No generic praise."),
            ),
        )
        # The schema needs a single named object at the top, not a bare array — hence the
        # envelope. Same reason `Dataset` existed in module 3.
        Dataset = create_model("Dataset", cases=(list[TestCase], ...))

        prompt = f"""
Generate {num_cases} test cases for evaluating this task:

{task_description}

Each case supplies these inputs:
{json.dumps(prompt_inputs_spec, indent=2)}

* Make the cases genuinely different from each other — vary the numbers, the goals and the
  constraints, not just the names
* Include at least one case with an awkward or conflicting requirement, since that is where
  a weak prompt actually falls over
* solution_criteria must be specific enough that two people grading independently would
  agree
"""
        messages = []
        add_user_message(messages, prompt)

        # max_tokens sized to the OUTPUT being asked for. Under parse() a ceiling that is
        # too low does not truncate politely — the JSON stops mid-object and the whole call
        # fails validation.
        response = self.client.messages.parse(
            model=self.answer_model,
            max_tokens=8192,
            messages=messages,
            output_format=Dataset,
        )
        self.answer_tracker.record(response)

        dataset = [case.model_dump() for case in response.parsed_output.cases]

        out_path = Path(output_file)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(dataset, f, indent=2)

        print(f"Generated {len(dataset)} cases → {out_path.name}")
        return dataset

    # ── step 3: run one case ─────────────────────────────────────────────────────────

    def _run_one(self, run_prompt_function, test_case: dict, extra_criteria: str) -> dict:
        """Answer one case, then grade that answer. Runs on a worker thread."""
        prompt_inputs = test_case["prompt_inputs"]

        output = run_prompt_function(self.client, prompt_inputs, self.answer_tracker)
        grade = self._grade(test_case, output, extra_criteria)

        return {
            "prompt_inputs": prompt_inputs,
            "output": output,
            "score": grade["score"],
            "reasoning": grade["reasoning"],
            "strengths": grade["strengths"],
            "weaknesses": grade["weaknesses"],
            "solution_criteria": test_case["solution_criteria"],
        }

    def _grade(self, test_case: dict, output: str, extra_criteria: str) -> dict:
        """Score one answer out of 10 against this case's criteria."""
        criteria = "\n".join(f"- {c}" for c in test_case["solution_criteria"])

        # f-string. A plain string here would send the grader the literal text "{output}"
        # and it would still return a confident score for content it never saw — the
        # single worst failure in module 3, because nothing looks wrong.
        eval_prompt = f"""
You are grading the output of an AI assistant. Be strict and specific.

The inputs it was given:
{json.dumps(test_case["prompt_inputs"], indent=2)}

Criteria this specific case must satisfy:
{criteria}
{extra_criteria}

The output to grade:
{output}

Score out of 10, where 10 means every criterion above is fully met and 1 means the output
ignores the task. Justify the score against the criteria, not against general writing
quality.
"""
        messages = []
        add_user_message(messages, eval_prompt)

        response = self.client.messages.parse(
            model=self.grader_model,
            max_tokens=MAX_TOKENS,
            messages=messages,
            output_format=Grade,
        )

        with self._lock:
            self.grader_tracker.record(response)

        return response.parsed_output.model_dump()

    # ── step 4: run the whole evaluation ─────────────────────────────────────────────

    def run_evaluation(self, run_prompt_function, dataset_file: str,
                       extra_criteria: str = "", report_file: str | None = None,
                       limit: int | None = None) -> list[dict]:
        """Run every case through the prompt, grade each, print the average.

        `run_prompt_function` is passed as a VALUE — `run_evaluation(run_prompt, ...)`, no
        parentheses. With parentheses Python would call it first and hand over its return
        value, and the evaluator would have a string where it expects something to call.

        `limit` runs only the first N cases, for cheap iteration while a prompt is still
        being drafted. Two rules come with it:

          * a limited score is NOT comparable with a full one. Fewer cases means a
            different average over a different set, not a noisier version of the same
            number. Compare limited runs with limited runs.
          * the answer to "is this prompt better" always comes from a full run.

        Generating a large dataset is a one-off cost of a few cents; running one is what
        adds up. So the dataset stays big and this trims what gets executed.
        """
        with open(dataset_file, encoding="utf-8") as f:
            dataset = json.load(f)

        total_cases = len(dataset)
        if limit is not None:
            dataset = dataset[:limit]
            # Say it out loud. A truncated run that prints a bare average looks exactly
            # like a full one, and that is how a partial result gets recorded as a result.
            print(f"!! Limited run: {len(dataset)} of {total_cases} cases. "
                  f"Not comparable with a full run.")

        if extra_criteria:
            extra_criteria = f"\nAdditional requirements for every case:\n{extra_criteria}"

        # Cases are independent, so they can run at the same time. Threads (not asyncio)
        # because an API call is spent waiting on the network, which releases the GIL —
        # and because nothing else in this repo is async. Keep the number low: too many at
        # once earns a 429.
        with ThreadPoolExecutor(max_workers=self.max_concurrent_tasks) as pool:
            results = list(pool.map(
                lambda case: self._run_one(run_prompt_function, case, extra_criteria),
                dataset,
            ))

        average = mean(result["score"] for result in results)
        print(f"\nAverage score: {average:.2f}  ({len(results)} cases)")

        # A truncated answer is graded on what survived, so it scores badly for a reason
        # that has nothing to do with the prompt. Say so next to the number rather than
        # further down in the cost line, where it reads as a footnote to a valid result.
        if self.answer_tracker.truncated:
            print(f"\n*** THIS SCORE IS NOT VALID ***\n"
                  f"    {self.answer_tracker.truncated} of {len(results)} answers hit "
                  f"max_tokens and were cut off mid-sentence.\n"
                  f"    Raise MAX_TOKENS in helpers.py and run it again before recording "
                  f"or comparing this number.")

        self.report_cost()

        if report_file:
            self._write_report(results, average, report_file)

        return results

    def report_cost(self) -> None:
        print("  answering: ", end="")
        self.answer_tracker.report()
        print("  grading:   ", end="")
        self.grader_tracker.report()
        total = self.answer_tracker.cost + self.grader_tracker.cost
        print(f"  total:     ~${total:.4f}")

    # ── the HTML report ──────────────────────────────────────────────────────────────

    def _write_report(self, results: list[dict], average: float, report_file: str) -> None:
        """Write a standalone HTML page — the scores alone never explain themselves."""
        rows = []
        for i, r in enumerate(results, 1):
            weaknesses = "".join(f"<li>{html.escape(w)}</li>" for w in r["weaknesses"])
            rows.append(f"""
  <details>
    <summary><b>Case {i}</b> — score <b>{r['score']}/10</b></summary>
    <p><b>Inputs</b></p><pre>{html.escape(json.dumps(r['prompt_inputs'], indent=2))}</pre>
    <p><b>Output</b></p><pre>{html.escape(r['output'])}</pre>
    <p><b>Reasoning</b></p><p>{html.escape(r['reasoning'])}</p>
    <p><b>Weaknesses</b></p><ul>{weaknesses}</ul>
  </details>""")

        page = f"""<!doctype html>
<meta charset="utf-8"><title>Eval report</title>
<style>
 body {{ font: 15px/1.6 system-ui, sans-serif; max-width: 900px; margin: 2rem auto; padding: 0 1rem; }}
 pre {{ background: #f4f4f5; padding: .75rem; border-radius: 6px; overflow-x: auto; white-space: pre-wrap; }}
 details {{ border: 1px solid #e4e4e7; border-radius: 6px; padding: .75rem; margin: .5rem 0; }}
 summary {{ cursor: pointer; }}
</style>
<h1>Average score: {average:.2f} / 10</h1>
<p>{len(results)} cases.</p>
{"".join(rows)}
"""
        Path(report_file).write_text(page, encoding="utf-8")
        print(f"  report:    {Path(report_file).name}")
