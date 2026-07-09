# Claude Code 101 — Notes

Course: [Claude Code 101](https://anthropic.skilljar.com/claude-code-101) · Status: ✅ Completed

Claude Code is Anthropic's AI coding tool that lives in your terminal — it can read
your codebase, make changes, run commands, and work like a coding agent (not just a chat).

## What I learned

- **Context & `/compact`** — the AI works within a limited context window. Keeping it
  clean matters; `/compact` summarizes the conversation so you don't lose the thread
  while freeing up space.
- **Subagents (basics)** — you can spin off separate agents to handle focused tasks,
  keeping the main conversation clean. Grasped the idea; want to go deeper later.
- **`/commit-push-pr`** — a command that handles the git flow (commit → push → PR) for you.
- **`CLAUDE.md`** — a project file that gives Claude persistent context/instructions
  about your codebase, so you don't repeat yourself every session.
- **Keeping the context window clean** — being deliberate about what's in context leads
  to better, more focused output.

## Key takeaways (from a frontend POV)

- **Context window = component render budget.** Just like you don't dump everything into
  one bloated component, you don't dump everything into the AI's context. Keep it lean.
- **`CLAUDE.md` is like a config/README the AI actually reads.** Set it once, stop
  repeating yourself — same idea as a shared eslint/prettier config for a team.
- **Subagents feel like code-splitting.** Offload a focused task to a separate agent so
  the main thread stays fast and clean.
- **It's an agent, not autocomplete.** You direct it like a junior dev — clear task,
  clear context — not like a search box.

## Still to go deep on

- **Skills** — reusable capabilities/instructions for the agent.
- **MCP (Model Context Protocol)** — connecting the agent to external tools/data.
- **Hooks** — automating actions around the agent's workflow.

_(These come up properly in later courses — noted here to revisit.)_

## Questions I still have

- _(add anything unclear to revisit later)_
