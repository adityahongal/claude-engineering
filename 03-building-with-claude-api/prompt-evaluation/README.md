# Prompt Evaluation

Measuring whether a prompt actually works, instead of deciding by eye. The module comes
before prompt engineering on purpose — you can't tell whether a change helped until you
can score it.

## Notes

**Evaluation vs engineering**

Two halves of the same loop:

- **Prompt engineering** — writing and rewriting the prompt. The craft.
- **Prompt evaluation** — measuring whether a rewrite made things better. The feedback.

Engineering without evaluation is guessing that happens to be well-informed. You change
something, the next answer looks good, and you conclude the change worked — when the model
might simply have sampled differently. Evaluation is what turns "seems better" into
"scored 8.7 against 7.66".

**Measuring effectiveness**

The point is a **number you can compare**. Prose judgements don't stack up against each
other; scores do. Once each prompt version has one, picking the better version stops being
an argument.

**Automation**

Reading answers yourself works for three examples and collapses at three hundred. Automating
the scoring is what makes it realistic to re-run the whole dataset on every tweak — which is
the only way the loop stays honest as the prompt grows.

**Three paths after drafting a prompt**

| Path | Cost | Worth it when |
|---|---|---|
| Test once, decide if it's good enough | Free | Throwaway or low-stakes work |
| Test a few times, including edge cases | Minutes | Small tools, one-off scripts |
| Run it through an eval pipeline and score it | Setup effort + API calls | Anything shipping, or any prompt you'll keep changing |

All three are legitimate. The mistake is defaulting to the first without noticing you chose.

**The testing trap**

Trying a prompt on one or two inputs, seeing it work, and concluding it's good. Two things
go wrong:

- **Small samples plus model variance.** The same prompt can produce a great answer and a
  poor one on consecutive runs. One good result is not evidence.
- **Tuning and testing on the same examples.** If you keep adjusting until those three
  questions look right, you've measured how well you fitted those three questions — not
  how the prompt handles the next one.

**Metrics**

A grader scores each response, typically 1–10, and the scores average into one number for
the prompt version. Change the prompt, re-run, compare averages.

**The workflow**

```
draft a prompt  →  build an eval dataset  →  run each case through Claude
                        →  score each answer with a grader  →  change the prompt, repeat
```

Worked through step by step, with the course's example, in
[`typical_prompt_eval_workflow.py`](./typical_prompt_eval_workflow.py).

**Generating the dataset with Claude**

Hand-writing an eval set is fine for three rows and tedious at three hundred, so the
dataset itself is worth generating. Describe the kind of task you want, declare the shape
you want it in, and write the result to disk:

```python
class Task(BaseModel):
    task: str

class Dataset(BaseModel):
    tasks: list[Task]

response = client.messages.parse(messages=messages, output_format=Dataset)
return [task.model_dump() for task in response.parsed_output.tasks]
```

`Task` describes one row, `Dataset` is the envelope holding the list — the schema needs a
single named object at the top, not a bare array. `parse` sends that schema with the
request, constrains generation to fit it, and validates the reply into real objects.
`model_dump()` converts them back to plain dicts, because `json.dump` can only write
built-in types.

Validation has moved. The usual pattern is to validate a dict *after* it arrives and handle
`ValidationError`; here the wrong shape can't be generated in the first place.

Because it's generated, the dataset is worth **committing** rather than regenerating each
run — an eval set that changes underneath you isn't a baseline.

**Size `max_tokens` to the output you asked for.** Twenty rows of task descriptions came
back as 1,376 output tokens. The original 1024 ceiling would have cut the JSON off
mid-object, and under `parse` that isn't a truncated-but-usable answer — the reply fails
validation and the whole call raises. Under `create` it's quieter and worse: you get a
half-answer that looks fine. Whenever the requested output grows, the ceiling has to grow
with it.

**Check the shape of what came back, not just the count.** Asking for a spread across
three formats doesn't guarantee one. A run that returns 18 Python tasks and 1 JSON leaves
two of the three validators barely exercised, and the average score hides it completely —
so the generator prints a per-format tally (here: 7 python / 7 json / 6 regex).

**The course's default JSON move is prefill**

Prefill plus `stop_sequences` recurs through the course whenever JSON is wanted, and it
400s on current models. The standing translation:

> course says *prefill + `stop_sequences`* → write `messages.parse(output_format=Model)`

**Tracking tokens and cost**

Two mechanisms:

- **`response.usage`** — exact `input_tokens` / `output_tokens` for the call just made.
  Accumulate across a run to see what it really cost.
- **`client.messages.count_tokens(...)`** — counts the input a request *would* use without
  running the model. Free, so a large run can be priced before committing to it. Input
  only; output length isn't knowable until Claude has written it.

`usage_tracker.py` wraps both. `record()` returns the response, so it fits around an
existing call without restructuring:

```python
tracker = UsageTracker(MODEL)
response = tracker.record(client.messages.parse(...))
tracker.report()      # 6 calls | in 2,700 | out 1,650 | ~$0.0329
```

The figure that matters isn't one run — it's runs × iterations, because evaluating means
re-running constantly. On Sonnet, one answer plus one grade per task:

| Dataset | Per run | Runs on $5 |
|---|---|---|
| 3 tasks | ~$0.03 | ~150 |
| 25 tasks | ~$0.27 | ~18 |
| 100 tasks | ~$1.10 | ~4 |

Keep the dataset small while building the pipeline and grow it once the machinery works.
That's the trade made here: three rows while the graders were being wired up, 20 now that
they work — about **$0.22 a run**, so roughly 20 full runs on a $5 balance. Enough to
compare prompts properly, not enough to run carelessly.
Grading is also a simpler job than the task itself, so running the grader on
`claude-haiku-4-5` while answering on Sonnet cuts that half by roughly two thirds —
different models for different roles in one pipeline is normal, not a compromise.

**Running the eval**

Three layers, each one step more specific:

```
run_eval          for every task in the dataset...
  run_test_case     ...answer it and score it...
    run_prompt        ...by filling the template and calling Claude
```

Each collects what the one below returns: a string, wrapped into a result dict, gathered
into a list. It's split this way because grading slots into `run_test_case` — "everything
that happens to one row" is answer *and* judge.

Each result keeps `output`, `test_case` and `score` together. The grader needs the
original task to judge the answer against, and a bare score tells you the average moved
without telling you which task moved it.

The dataset is **read**, never regenerated here. Answers are written to `answers.json` so
grading — the part you iterate on — can re-run without paying to answer everything again.

**Truncation quietly poisons an eval**

A reply that hits `max_tokens` is **cut off, not finished**, and `stop_reason` says so. In
an eval that's worse than a normal bug: a truncated answer scores badly for a reason that
has nothing to do with the prompt being measured, so the baseline is wrong and every
comparison against it inherits the error.

Two of the first three answers here hit a 1024 ceiling — a regex with explanation and a
Python function with commentary. Character count is a poor guide, because code and JSON
tokenize denser than prose. `UsageTracker` now counts `stop_reason == "max_tokens"` and
warns, so it can't pass unnoticed.

**Model-based grading**

Three ways to grade: **code** (programmatic checks — length, valid syntax, forbidden
words), **model** (a second Claude call judging quality), **human** (most flexible, least
scalable). Format and syntax suit code graders; "did it actually address the task" suits a
model grader.

Ask for strengths and weaknesses **alongside** the score. Without them models drift toward
a safe 6 for everything; making the grader justify itself first spreads the scores out.

Use two models for two roles:

```python
MODEL        = "claude-sonnet-5"     # answers — the thing being evaluated
GRADER_MODEL = "claude-haiku-4-5"    # grades — simpler job, ~1/3 the cost
```

`MODEL` must stay fixed across runs or the scores aren't comparable — you'd be evaluating
a different model, not a different prompt. A single shared constant silently changes both.

Grade with a **schema**, not by parsing prose. The course's prefill route raised
`JSONDecodeError` intermittently on this dataset: the reasoning quotes regex, every
backslash has to be escaped correctly in JSON, and one miss kills the parse. A nested code
fence in the reasoning also trips `stop_sequences=["```"]` and truncates mid-object.
`score: int` in the schema pins the scale too — the prose version returned 6, 7.5 and 8
across three calls.

**Your noise floor**

Run the eval twice **without changing anything** before trusting any comparison. Two
identical runs here produced:

```
run 1: average 7.000
run 2: average 7.333    scores [6, 8, 8]
```

One score moved by a point; on a three-row dataset that's 0.333 of the average. So any
prompt change scoring less than ~0.33 better is indistinguishable from noise — 7.0 → 7.33
tells you nothing at all.

Two sources stack: the answer varies run to run, and the grade of a given answer varies
too. More rows is the fix — each score is worth 1/n of the average, so 30 rows gives ten
times the resolution of 3.

**Code-based grading**

A code grader parses the output instead of judging it: valid JSON, parses as Python, the
regex compiles. Free, instant, and **deterministic — the same input always scores the
same, so it adds no noise at all.**

It needs two things the model grader doesn't:

- **A prompt that asks for code only.** Parse a markdown answer full of headings and
  explanation and every check fails on the prose rather than the code.
- **A `format` on each dataset row**, so the right validator runs. `Literal["python",
  "json", "regex"]` on the schema keeps a regenerated dataset honest.

The validators take no `client` — they make no API call. "Missing `client`" is only ever a
bug in functions that talk to the API.

**Combining the two scores: gate, don't average**

```python
score = model_score if syntax_score == 10 else 0
```

Averaging a 1–10 judgement with a binary 0/10 distorts both ends — a syntax failure caps a
strong answer at 5, a syntax pass drags a weak one up toward 10. Code that doesn't parse
is worthless whatever the intent, so it scores 0. Keep both components in the result so a
0 is explainable.

**The two graders catch different things.** A real run here:

```
1. format=regex   final=0   model=5  syntax=0     <- (?<name>) is JavaScript; Python needs (?P<name>)
2. format=python  final=7   model=7  syntax=10
3. format=json    final=8   model=8  syntax=10
```

The model grader read that regex, judged it reasonable and gave it 5. It never noticed the
pattern won't compile. The code grader caught it instantly and for free. A model grader
judges *plausibility*; a code grader checks *fact*.

## Noise floor

**The smallest change in the average that means anything.** Run the eval twice with
nothing changed — whatever the two averages differ by is noise, and any prompt change
producing a smaller delta than that has told you nothing.

Measured here, twice:

| Setup | Runs | Noise floor |
|---|---|---|
| Model grader only, 3 rows | 7.000 / 7.333 | ~0.33 |
| Model + syntax gate, 3 rows | 7 / 5 | ~2.0 |

The gate made it far worse — one case flipping now swings the mean by over two points
instead of a third of one. That isn't a reason to soften the gate; the underlying
instability is real (Claude genuinely writes a non-compiling regex some of the time) and
the eval is correctly reporting a flaky prompt.

Both of those numbers came off a three-row dataset, where one case *is* a third of the
score. `dataset.json` is 20 rows from here on, which should pull the floor down by roughly
the square root of the row increase — but that's a prediction, not a measurement. Run it
twice unchanged and find out before trusting any prompt comparison built on it.

**Where the noise comes from**

1. The answer varies — same prompt, different solution each run
2. The grade varies — the model grader judges the same answer slightly differently
3. Binary gates amplify both: a case doesn't drift a point, it jumps the full range

**How to lower it**

- **More rows.** The biggest lever by far. Each case is worth 1/n of the average, so 30
  rows gives ten times the resolution of 3. Scores × cost both scale linearly; resolution
  scales with them.
- **Run each case more than once and average** before averaging across cases. Costs
  multiply, but it attacks per-case variance directly.
- **Tighten the rubric.** Vague criteria let the grader wander; explicit ones ("10 = runs
  as written and handles the stated edge cases") produce steadier scores.
- **Lower the temperature** — unavailable on `claude-sonnet-5`, where it's removed, so on
  current models this lever is gone and dataset size has to do the work.
- **Prefer code graders where a check is possible.** They contribute exactly zero noise.

Practical rule: **measure the floor before reading any improvement.** A 0.4 gain against a
2.0 floor isn't an improvement, it's a coin flip.

## Frontend mental model

- **The eval dataset is a test suite.** Fixed inputs you re-run after every change.
- **The grader is the assertion**, except it returns a score rather than pass or fail.
- **The average is your pass rate** — the single number you watch move.
- Changing a prompt with no evals is shipping with no tests because it worked when you
  clicked it once.

## Gotchas

- **The same prompt gives different answers run to run.** Any conclusion from a single
  response is noise, not signal.
- **Tune and test on the same examples and you're measuring overfitting.** Keep held-back
  cases the prompt was never adjusted against.
- **Make the grader return structured output.** Ask for a score in prose and you'll be
  parsing `"I'd give this an 8/10"` out of a paragraph. A Pydantic model with
  `score: int` gives you something you can average.
- **An average hides its distribution.** 10, 4, 9 and 7, 8, 8 both average ~7.7, but one
  has a failure in it. Look at the low scores, not just the mean.
- **Every dataset row costs two calls** — one to answer, one to grade. Cost scales with
  the dataset, not the prompt.
- **State belongs to the function that uses it.** A `messages` list is scratch state for
  one request; defining it in the caller means the callee references a name it can't see.
  Most "I can't get this to work" structural bugs are something living in the wrong place.
- **`extra_body` gets a parameter past the SDK, not past the server.** It can't rescue
  `temperature` on a model that rejects it.
- **`json.dump` can't write Pydantic objects** — `TypeError: Object of type Task is not
  JSON serializable`. Call `model_dump()` first. Objects in the middle, plain dicts at the
  edges.
- **A code grader only works if the prompt asks for code only.** Otherwise every check
  parses markdown prose and fails for reasons unrelated to the code.
- **"Missing `client`" applies only to functions that call the API.** `json.loads`,
  `ast.parse` and `re.compile` are local — passing a client raises `TypeError: loads()
  takes 1 positional argument`.
- **Changing the prompt voids the baseline.** A new prompt is a different thing being
  measured; the old average no longer compares.
- **Measure the noise floor before reading any improvement.** Run the eval twice unchanged.
  Whatever the averages differ by is the smallest change that means anything.
- **A missing `f` prefix fails silently and is the worst bug in the module.** `{task}` and
  `{solution}` go through as literal text, the grader reviews placeholders, and it still
  returns a confident score. Nothing errors; the baseline is simply fiction.
- **Intermittent is worse than broken.** The prefill grader passed six consecutive calls
  while being fundamentally unreliable. A schema removes the failure mode instead of
  lowering its odds.
- **One shared `MODEL` constant for answering and grading changes what you're measuring**
  when you switch it for cost.
- **Check `stop_reason` before trusting an eval score.** `max_tokens` means the answer was
  cut off; grading it measures the ceiling, not the prompt.
- **Adding a parameter to a signature isn't the same as passing it at the call site.**
  Half-fixes like this compile fine and fail at runtime.
- **`dataset.json` is committed, `answers.json` is git-ignored.** The dataset is a stable
  input — a baseline that shifts isn't a baseline. The answers are derived output,
  regenerated whenever the prompt changes.
- **Don't describe the output shape in both the prompt and the schema.** With
  `output_format` the schema is the contract; an example JSON block in the prompt is
  redundant and can contradict it.

## Files

- `typical_prompt_eval_workflow.py` — the five-step workflow, annotated with the course's
  worked example.
- `generating_test_datasets.py` — asks Claude for the eval set, constrained to a Pydantic
  schema, and writes it to `dataset.json`. The course's prefill route is kept as a comment.
- `dataset.json` — the generated eval set. Committed on purpose: a baseline that changes
  between runs isn't a baseline.
- `usage_tracker.py` — running token totals and cost estimates, a `count_tokens` wrapper
  for pricing a run before making it, and a truncation warning.
- `running_the_eval.py` — reads the dataset, runs every task through the prompt, writes
  the answers to `answers.json` (git-ignored) for grading to pick up.
- `model_based_grading.py` — the full loop: answer on Sonnet, grade on Haiku against a
  rubric, average the scores. The grader uses a schema; the course's prefill route is kept
  as a comment with the failure it produced.
- `code_based_grading.py` — both graders together: syntax validators dispatched on the
  row's `format`, gated against the model score.

## Run

```bash
source ../../../.venv/bin/activate     # from this folder
python generating_test_datasets.py     # writes dataset.json alongside it
```
