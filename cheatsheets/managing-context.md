# Managing Context (in AI coding tools) — Cheatsheet

**The core idea:** AI models have a limited **context window** — the amount of text they
can "see" at once. A clean, focused context = better output. A cluttered one = confused,
generic output.

**Key concepts:**
- **Context window** — the working memory of the AI. Everything (your files, chat history,
  instructions) shares this space.
- **`/compact`** — summarizes the conversation so far, freeing up space without losing
  the important thread.
- **`CLAUDE.md`** — a project file with persistent instructions/context the AI reads every
  session. Set once, reuse forever.
- **Subagents** — offload a focused task to a separate agent so the main context stays clean.

**Frontend analogy:**
- Context window = your render budget. Don't bloat it.
- `CLAUDE.md` = a shared config the AI actually respects.
- Subagents = code-splitting for AI tasks.

**Why it matters:** Managing context well is the difference between an AI that "gets" your
project and one that keeps guessing. This idea scales beyond coding tools — it's the same
reason **RAG** exists (giving the model the *right* context, not all of it).
