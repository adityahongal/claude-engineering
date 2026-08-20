# Claude Code

Anthropic's coding tool that lives in your terminal. It reads your codebase, makes
changes, and runs commands — closer to an agent than a chat window.

Source: Anthropic Academy — [Claude Code 101](https://anthropic.skilljar.com/claude-code-101)

## Core concepts

- **Context and `/compact`** — it works inside a limited context window, so keeping that
  window clean matters. `/compact` summarizes the conversation so you don't lose the
  thread while freeing up space.
- **Subagents** — spin off a separate agent for a focused task so the main conversation
  stays clean.
- **`/commit-push-pr`** — one command that handles the whole git flow (commit → push →
  PR).
- **`CLAUDE.md`** — a project file that gives Claude persistent context about your
  codebase, so you're not repeating yourself every session.
- **Being deliberate about context** — what you let into context directly changes how
  focused the output is.

## Frontend mental model

- **The context window is a render budget.** You wouldn't dump everything into one
  bloated component; same idea here. Keep it lean.
- **`CLAUDE.md` is config the agent actually reads.** Set it once and stop repeating
  yourself — same role a shared ESLint or Prettier config plays for a team.
- **Subagents feel like code splitting.** Hand a focused task to a separate agent so the
  main thread stays fast.
- **It's an agent, not autocomplete.** You direct it the way you'd brief a teammate —
  clear task, clear context — not the way you'd use a search box.

## Related topics

Skills, MCP, and hooks show up here but get covered properly in
[`../02-platform-101/`](../02-platform-101/) and the MCP modules.
