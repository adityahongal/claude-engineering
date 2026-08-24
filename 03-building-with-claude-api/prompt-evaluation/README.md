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

## Files

- `typical_prompt_eval_workflow.py` — the five-step workflow, annotated with the course's
  worked example.
