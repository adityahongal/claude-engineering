# Prompt Engineering Techniques

Four techniques for changing a prompt, and the habit of checking whether the change
actually helped. This module is the other half of the loop started in
[`../prompt-evaluation/`](../prompt-evaluation/): that folder built something that can tell
a real improvement from a lucky run, and without it every technique here is opinion.

## Notes

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

## Files

- `helpers.py` — shared plumbing: client setup, message builders, `chat`, error handling
- `prompt_engineering.py` — what the techniques are for, and where they sit next to evaluation
- `being_clear_and_direct.py` — stating the task, the audience, and what "done" looks like
- `being_specific.py` — constraints on format, length, omissions, and edge cases
- `structure_with_xml_tags.py` — separating instructions from data in a long prompt
- `providing_examples.py` — showing the shape of the answer instead of describing it

The course also has an exercise and a quiz for this module; neither produces a file.

## Run

```bash
cd 03-building-with-claude-api/prompt-engineering
python being_clear_and_direct.py
```

The virtual environment and `.env` are shared — see the
[module README](../README.md#setup).
