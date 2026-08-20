# Claude Fundamentals

What Claude actually is, how prompting works, and why context decides how good the output
is.

Source: Anthropic Academy — [Claude 101](https://anthropic.skilljar.com/claude-101)

## Scope

- Claude is a large language model — it understands and generates natural language.
- The whole interaction is prompts in, responses out.
- The basics that matter: what a prompt is, how to give context, and why being specific
  changes everything.
- Where it runs: chat, and through the API, inside your own apps.

## Frontend mental model

- **A prompt works like props.** What you pass in shapes what comes back — garbage in,
  garbage UI. Being specific matters just as much here as it does with component props.
- **Context is state management.** The model only knows what you hand it in that moment.
  Give it the right context and the output stays consistent; leave it vague and it
  guesses.
- **It can't read your mind.** You have to spell out the format, the tone, the goal.
  Honestly it feels a lot like debugging CSS — the fix is usually "I didn't say exactly
  what I meant."
- **Prompt engineering is a real skill**, not a buzzword. It's the gap between an okay
  answer and one you'd actually ship.

## Glossary

- **Prompt** — the instruction or message you send to the model.
- **Context** — the background info you give it so the answer fits what you actually need.
- **LLM (Large Language Model)** — the kind of model Claude is, trained on a huge amount
  of text.
