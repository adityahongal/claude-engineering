# Prompt Engineering Techniques

Four techniques for changing a prompt, and the habit of checking whether the change
actually helped. This module is the other half of the loop started in
[`../prompt-evaluation/`](../prompt-evaluation/): that folder built something that can tell
a real improvement from a lucky run, and without it every technique here is opinion.

## Notes

**What the module measures, and how it differs from the last one**

The running example is a one-day meal plan for an athlete. The shape of a test case changed
from the previous folder, and the difference is the whole point of the module:

| | prompt evaluation | prompt engineering |
|---|---|---|
| A dataset row | a complete `task` string | `prompt_inputs` — height, weight, goal, restrictions |
| Under test | which task was asked | the **template** those inputs are dropped into |
| Grading | model score + syntax gate | model score against `solution_criteria` + `extra_criteria` |

So the inputs are frozen and committed, and the only thing that moves between lessons is
the wording wrapped around them. That is what makes two scores comparable at all. The
20-row AWS dataset in [`../prompt-evaluation/`](../prompt-evaluation/) still guards that
folder's prompt — it is a different experiment, not a superseded one.

**The evaluator**

The course hands you a `PromptEvaluator` class. `prompt_evaluator.py` is the local
equivalent, assembled from the pipeline built by hand in module 3 — same three steps (run
the prompt, grade the answer, average the scores), packaged so a lesson is a few lines.

```python
evaluator = PromptEvaluator(client, max_concurrent_tasks=3)
evaluator.generate_dataset(task_description=..., prompt_inputs_spec=..., num_cases=3)
evaluator.run_evaluation(run_prompt_function=run_prompt, dataset_file=..., extra_criteria=...)
```

Points worth knowing about it:

- **`create_model` builds the schema at runtime.** The field names come from
  `prompt_inputs_spec`, so they aren't known when the file is written. `create_model(...)`
  is a `class` statement assembled from a dict — same result, built from an argument.
- **`run_prompt(client, prompt_inputs, tracker)` takes three arguments here**, where the
  course version takes one. In a notebook `client` is a global that every cell can see; a
  script has no such namespace, so the evaluator passes it in.
- **Cases run on threads.** An API call is spent waiting on the network, so three at once
  finishes in roughly the time of one. Keep the number low or you earn a `429`.
- **Two trackers, two models.** Answering on Sonnet, grading on Haiku. One combined total
  would hide that grading is the cheap half.
- **`solution_criteria` are generated per case.** A grader given concrete, checkable
  criteria is steadier than one asked for a general impression — it directly lowers the
  noise floor.

**Sizing the dataset against a budget**

Two costs that look similar and behave nothing alike:

| | cost | how often |
|---|---|---|
| Generating cases | ~$0.01–0.03 | once, ever |
| Running 3 cases | ~$0.06 | every single run |

**Measured**, from the first two real runs: about **1.9¢ per case** — roughly 1.5¢ for the
Sonnet answer and 0.45¢ for the Haiku grade. The estimate beforehand was 1.5¢, so the
guess came in about a quarter low; the grader writes more reasoning than expected, and
reasoning is output tokens. Take the tracker's number over any table, including this one.

At 1.9¢ a case, a module with a baseline, four techniques and some re-running lands near
twelve full runs: about **$0.68 at three cases, $2.25 at ten**.

Generating big is nearly free; running big is what adds up. And the asymmetry only goes
one way — a subset of a large dataset is always available, while a superset of a small one
means regenerating, which makes every score already recorded incomparable.

`run_evaluation(..., limit=3)` trims what actually executes while a prompt is still being
drafted. A limited score is not a rougher version of the full score — it is a different
average over a different set, so compare limited with limited and settle the question with
a full run.

The committed `dataset.json` holds **3 cases**, generated before `num_cases` was raised to
10. Raising that number changes nothing on its own: generation is skipped whenever the file
exists, which is deliberate — regenerating would make every score below incomparable. The
script prints the real count on each run so the two can't quietly drift apart.

## Results

Same dataset, same criteria, same grader, three cases. Only the prompt changed, one
technique at a time, each building on the last.

| Prompt | Scores | Average | Output tokens | Answer cost |
|---|---|---|---|---|
| Naive baseline | 5, 5, 7 | 5.67 | 2,814 | $0.043 |
| Clear and direct | 8, 8, 8 | **8.00** | 3,175 | $0.049 |
| Being specific | 9, 9, 9 | **9.00** | 6,235 | $0.096 |
| XML tags | 9, 9, 9 | 9.00 | 13,627 | $0.208 |
| Providing examples | 9, 9, 9 | 9.00 | 8,133 | $0.128 |

**The noise floor, measured here rather than assumed.** The baseline was accidentally run
twice — same prompt, same dataset — scoring `7, 4, 7` (6.00) and `5, 5, 7` (5.67). So the
floor on the average is about **0.33**, matching the previous module. The per-case numbers
are far wilder: individual cases moved by up to 2 points between identical runs. The
average is much steadier than anything inside it, which is the entire reason for averaging.

That also killed a tempting story. On the first run the baseline scored 4 on the vegan
case, which looked like "the weak prompt collapses on hard constraints". The second run
scored that same case 5 and dropped an easy one to 5 instead. One sample of a noisy signal
will happily support a narrative it cannot actually carry. The defensible claim is duller:
**the baseline sits near 5.7–6.0 and is inconsistent.**

**Everything real happened in the first two steps.** Clear and direct bought +2.3, being
specific another +1.0. Then it stopped. XML tags and worked examples both scored exactly
9.00 — no movement at all, well inside noise.

That is a genuine result, not a failed experiment. Those techniques earn their keep on
prompts that mix large or ambiguous blocks of content; this one is four short labelled
fields and a list, already unambiguous, and by then the grader's remaining complaints were
nitpicks ("didn't show the macro calculation working", "no micronutrient discussion").
There was no headroom left for a formatting technique to win.

**Cost is where they differ, and it diverges sharply.** All three of the last prompts score
9.00, but XML tags cost **2.2× more per run** than being specific for exactly the same
score, and examples 1.3× more. Structure made Claude write far more, not better. Scoring a
prompt on quality alone hides that completely — the cheapest prompt at a given score is the
one to ship.

**Providing examples: the copying trap did not fire.** The worked example is a chicken and
eggs plan for an athlete with no restrictions, and the dataset includes a vegan case and a
lactose-intolerant one. Three explicit "adapt, do not copy" lines were enough — the vegan
plan borrowed nothing, and the lactose-intolerant plan used almond milk and lactose-free
substitutes. Without those lines this is the technique most likely to produce a confidently
wrong answer.

**The helper module**

The previous two folders hand-wrote the same four things in every file: `load_dotenv()`
plus a key check, `add_user_message`, a `chat()` wrapper around `messages.create`, and the
`except` chain in `main()`. None of that is what this module is about, so it moved into
`helpers.py` and gets imported.

Two additions on top of what was there before:

- `ask(client, prompt)` — one prompt in, one reply out, building its throwaway `messages`
  list internally. Most lessons here send a single prompt with no history.
- `compare(client, {label: prompt})` — runs several wordings of the same request and
  prints each reply under its label, which is the shape of nearly every lesson.

Each call inside `compare` starts from a **fresh** message list. Reusing one list would
append reply A before prompt B and quietly turn a comparison into a conversation, where
the second answer is influenced by the first.

`run(main)` takes the function itself — no parentheses. `run(main())` would call `main`
first and pass its return value, which defeats the point: the error handling has to be
wrapped *around* the call, not applied to its result.

Reading two replies side by side is an impression, not a measurement. When a change
actually needs proving, that's what [`../prompt-evaluation/`](../prompt-evaluation/) is
for — with a 20-row dataset and a measured noise floor to compare against.

## Gotchas

- **`compare` costs one API call per entry in the dict.** Three wordings is three calls.
- **Change one thing at a time.** If the improved prompt also asks for something slightly
  different, the comparison measures both changes and attributes them to the technique.
- **f-strings when a prompt interpolates anything.** A plain string sends the literal
  `{DOCUMENT}` and Claude answers about nothing, confidently — the failure is silent.
- **`helpers.py` reaches into the sibling folder** for `usage_tracker.py` via a `sys.path`
  insert rather than keeping a second copy that would drift. Packaging is the real fix;
  two explicit lines are the honest trade for a folder of exercises.
- **Generate `dataset.json` once, then leave it.** Regenerating it makes every score from
  every previous lesson incomparable. `prompt_engineering.py` skips generation if the file
  already exists, so re-running it is safe.
- **`messages.parse` sends the schema as `output_config`, not `output_format`.** The
  keyword argument and the wire format have different names — worth knowing if you ever
  inspect a request body or write a mock against one.
- **`parse` reads its JSON out of a `text` block**, not a `tool_use` block. The structured
  output arrives as ordinary text that the SDK then validates.
- **A shared counter across threads needs a lock.** `tracker.record()` does `+=`, which is
  a read then a write; two threads can interleave between the two halves and lose a count.
- **A wrong key in the prompt is free; a missing one is expensive.** `prompt_inputs["typo"]`
  raises `KeyError` while the f-string is built, before any request goes out — zero API
  calls, immediate traceback. Silently *omitting* an input is the dangerous one: it runs,
  returns a plausible score, and that score measures the wording change and the lost
  information together. Dropping `goal` from the improved prompt would likely have scored
  *below* the baseline and made the technique look harmful.
- **Read the per-case scores, not just the average.** A prompt that scores 7, 4, 7 is not
  a "6.0 prompt" — it is a prompt with one failure mode, and the average hides which case
  and why.
- **Raising `num_cases` does nothing while `dataset.json` exists.** That is the intended
  behaviour; delete the file deliberately to regenerate, and expect every prior score to
  become incomparable when you do.
- **A truncated answer scores badly for the wrong reason.** The XML run hit a 4096
  `max_tokens` ceiling on two of three cases; one answer came back empty and was graded
  **1/10**, producing a confident, meaningless 5.33 average. Re-run untruncated it scored
  9.00. `max_tokens` now sits at 8192, and `run_evaluation` prints a loud *THIS SCORE IS
  NOT VALID* block next to the average rather than a footnote further down.
- **Raising a ceiling cannot invalidate earlier results.** A limit only affects answers that
  actually reached it, and none of the earlier runs did — so the 8192 change left every
  previous score comparable.
- **A more structured prompt is not a shorter one.** Wrapping the same content in XML tags
  roughly doubled the output. Structure changes how much Claude writes, so cost has to be
  read alongside score, never instead of it.
- **Judge a technique on cost per unit of score.** Three prompts here score an identical
  9.00 at $0.096, $0.128 and $0.208 a run. The score alone says they are equivalent; the
  bill says one is twice the price for nothing.

## Files

- `helpers.py` — shared plumbing: client setup, message builders, `chat`, error handling
- `prompt_evaluator.py` — the `PromptEvaluator` class: generate a dataset, run, grade, report
- `prompt_engineering.py` — the naive baseline prompt and the score everything is measured against
- `being_clear_and_direct.py` — stating the task, the audience, and what "done" looks like
- `being_specific.py` — constraints on format, length, omissions, and edge cases
- `structure_with_xml_tags.py` — separating instructions from data in a long prompt
- `providing_examples.py` — showing the shape of the answer instead of describing it

The course also has an exercise and a quiz for this module; neither produces a file.

## Run

Order matters — the baseline generates `dataset.json`, and every later lesson reads it.

```bash
cd 03-building-with-claude-api/prompt-engineering

python prompt_engineering.py       # baseline score, generates dataset.json if absent
python being_clear_and_direct.py   # each technique builds on the previous one
python being_specific.py
python structure_with_xml_tags.py
python providing_examples.py
```

Each writes a `report_*.html` next to itself — open it to see per-case scores, the full
output, and the grader's reasoning. Reports are git-ignored; they are regenerated on every
run.

The virtual environment and `.env` are shared — see the
[module README](../README.md#setup).
