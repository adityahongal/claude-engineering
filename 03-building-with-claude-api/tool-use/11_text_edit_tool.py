"""The text edit tool.

An Anthropic-defined tool: Claude knows the schema already, but you still implement the
behaviour. The contract is fixed, the execution is yours.
"""
# Claude comes with one built-in tool that you don't need to create from scratch: the text editor tool. 
# This tool gives Claude the ability to work with files and directories just like you would in a standard text editor.

# What the Text Editor Tool Can Do

# The text editor tool provides Claude with a comprehensive set of file manipulation capabilities:
# - View file or directory contents
# - View specific ranges of lines in a file
# - Replace text in a file
# - Create new files
# - Insert text at specific lines in a file
# - Undo recent edits to files

# Understanding the Implementation Requirements

# Here's where things get a bit confusing: while the tool schema is built into Claude, you still need to provide the actual implementation. 
# Think of it this way - Claude knows how to ask for file operations, but you need to write the code that actually performs those operations.
# When you use other tools, you write both the JSON schema and the function implementation. 
# With the text editor tool, Claude provides the schema knowledge, 
# but you must write functions to handle Claude's requests to create files, read directories, replace text, and so on.

# Schema Versions

# While the main schema is built into Claude, you do need to include a small schema stub when making requests. 
# The exact schema depends on which Claude model you're using:

# def get_text_edit_schema(model):
#     if model.startswith("claude-3-7-sonnet"):
#         return {
#             "type": "text_editor_20250124",
#             "name": "str_replace_editor",
#         }
#     elif model.startswith("claude-3-5-sonnet"):
#         return {
#             "type": "text_editor_20241022", 
#             "name": "str_replace_editor",
#         }
# Claude sees this small schema and automatically expands it into the full text editor tool specification behind the scenes.

# Why Use the Text Editor Tool?

# You might wonder why this tool exists when modern code editors already have AI assistants built in. 
# The text editor tool becomes valuable in scenarios where:
# - You're building applications that need to programmatically edit files
# - You're working in environments without access to full-featured code editors
# - You want to integrate file editing capabilities directly into your Claude-powered applications

# ─────────────────────────────────────────────────────────────────────────────────────
# DRIFT: the schema stub in the notes is two generations old.
#
#   course:  {"type": "text_editor_20250124", "name": "str_replace_editor"}   (3.7 Sonnet)
#   now:     {"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}
#
# The NAME changed too, not just the date — and the name is what arrives in block.name,
# so dispatch keyed on the old one silently matches nothing. The model-picking function
# in the notes has nothing to pick between any more: every current model takes this one.
#
# And the command set shrank. "Undo recent edits" in the notes was the `undo_edit` command;
# the current version has four:
#
#   view          path, optional view_range [start, end]    file with line numbers, or a
#                                                           directory listing
#   create        path, file_text                           new file (or overwrite)
#   str_replace   path, old_str, new_str                    replace EXACTLY one match —
#                                                           zero or several is an error
#   insert        path, insert_line, insert_text            after line N; 0 = the top
#
# Undo is now your job, if you want it — this file keeps a backup before every write.
# ─────────────────────────────────────────────────────────────────────────────────────
#
# "The schema is built in, the execution is yours" has a consequence the notes skip: the
# `path` Claude sends is untrusted model output, and your code is about to write to it.
# Nothing in the tool stops a request for ../../.ssh/config. So every path goes through
# resolve() first, and anything that lands outside the sandbox is refused — after
# resolving, so `..` and symlinks are caught, not just a string prefix.
#
# Claude is told the project lives at /repo. That path is fake: it maps onto a temporary
# directory, so the real filesystem layout never reaches the model, and the run leaves
# nothing behind.

import subprocess
import sys
import tempfile
from pathlib import Path, PurePosixPath

from helpers import UsageTracker, get_client, run, run_conversation, text_from

MODEL = "claude-sonnet-5"
TOOL_NAME = "str_replace_based_edit_tool"
VIRTUAL_ROOT = PurePosixPath("/repo")

# The whole schema. Claude expands the type into the full tool definition itself.
text_editor_schema = {"type": "text_editor_20250728", "name": TOOL_NAME}

SEED = '''def average(nums):
    return sum(nums) / len(nums)


def spread(nums):
    return max(nums) - min(nums)
'''


class TextEditor:
    """The implementation behind the built-in schema, confined to one directory."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.backups = {}   # path -> text before the last write, so an edit can be undone

    # ── the guard ────────────────────────────────────────────────────────────────────

    def resolve(self, path: str) -> Path:
        """Map a /repo/... path onto the sandbox, refusing anything that escapes it."""
        virtual = PurePosixPath(path)
        if virtual.is_absolute():
            if not virtual.is_relative_to(VIRTUAL_ROOT):
                raise ValueError(f"{path} is outside {VIRTUAL_ROOT}")
            virtual = virtual.relative_to(VIRTUAL_ROOT)
        # resolve() BEFORE the check: it collapses `..` and follows symlinks, so the
        # comparison is against where the write would really land.
        target = (self.root / virtual).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError(f"{path} is outside {VIRTUAL_ROOT}")
        return target

    def show(self, target: Path) -> str:
        return str(VIRTUAL_ROOT / target.relative_to(self.root))

    # ── dispatch ─────────────────────────────────────────────────────────────────────

    def __call__(self, command, path, **params):
        """run_tool calls this with block.input spread as keywords."""
        handler = getattr(self, f"cmd_{command}", None)
        if handler is None:
            # undo_edit lands here: the notes list it, the current tool version has no such
            # command. Claude reads the error and works without it.
            raise ValueError(f"unknown command {command!r}; "
                             "expected view, create, str_replace or insert")
        return handler(self.resolve(path), **params)

    # ── the four commands ────────────────────────────────────────────────────────────

    def cmd_view(self, target, view_range=None, **_):
        if target.is_dir():
            entries = sorted(p for p in target.rglob("*") if not p.name.startswith("."))
            return "\n".join(self.show(p) + ("/" if p.is_dir() else "") for p in entries)
        lines = self.read(target).splitlines()
        start, end = (view_range or [1, -1])
        end = len(lines) if end == -1 else end
        if not 1 <= start <= max(end, 1):
            raise ValueError(f"view_range {view_range} is invalid for {len(lines)} lines")
        # Numbered, cat -n style: the line numbers are what Claude uses for insert_line.
        return "\n".join(f"{n:6}\t{line}" for n, line in enumerate(lines, 1)
                         if start <= n <= end)

    def cmd_create(self, target, file_text, **_):
        if target.exists():
            self.backups[target] = self.read(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file_text)
        return f"created {self.show(target)}"

    def cmd_str_replace(self, target, old_str, new_str="", **_):
        text = self.read(target)
        count = text.count(old_str)
        # Exactly one. Zero means Claude's picture of the file is stale; several means the
        # edit is ambiguous — either way, guessing which one it meant is how files get
        # corrupted. The error tells it what to do instead.
        if count == 0:
            raise ValueError(f"old_str not found in {self.show(target)}; view the file "
                             "and copy the text exactly, whitespace included")
        if count > 1:
            raise ValueError(f"old_str matches {count} places in {self.show(target)}; "
                             "include more surrounding lines so it matches exactly one")
        self.backups[target] = text
        target.write_text(text.replace(old_str, new_str, 1))
        return f"edited {self.show(target)}"

    def cmd_insert(self, target, insert_line, insert_text=None, new_str=None, **_):
        # Older versions of this command called the text new_str; accept either.
        text_to_insert = insert_text if insert_text is not None else new_str
        if text_to_insert is None:
            raise ValueError("insert needs insert_text")
        text = self.read(target)
        lines = text.splitlines(keepends=True)
        if not 0 <= insert_line <= len(lines):
            raise ValueError(f"insert_line {insert_line} is outside 0..{len(lines)}")
        if not text_to_insert.endswith("\n"):
            text_to_insert += "\n"
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        self.backups[target] = text
        lines.insert(insert_line, text_to_insert)
        target.write_text("".join(lines))
        return f"inserted after line {insert_line} of {self.show(target)}"

    def undo(self, target: Path) -> None:
        """Not a tool command any more — but the backup makes it a one-liner for you."""
        target.write_text(self.backups.pop(target))

    def read(self, target: Path) -> str:
        if not target.is_file():
            raise ValueError(f"{self.show(target)} does not exist")
        return target.read_text()


def show_turn(turn, response, results):
    print(f"  turn {turn}: stop_reason={response.stop_reason}")
    for block, result in zip([b for b in response.content if b.type == "tool_use"],
                             results or []):
        args = {k: v for k, v in block.input.items() if k not in ("command", "path")}
        brief = {k: (v if len(str(v)) < 40 else str(v)[:37] + "...") for k, v in args.items()}
        status = "ERROR: " + result["content"] if result["is_error"] else result["content"]
        print(f"          {block.input.get('command')} {block.input.get('path')} {brief}")
        print(f"            -> {status.splitlines()[0] if status else ''}")


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    with tempfile.TemporaryDirectory() as tmp:
        editor = TextEditor(Path(tmp))
        stats = Path(tmp) / "stats.py"
        stats.write_text(SEED)

        # The guard, checked before Claude gets anywhere near it.
        for attempt in ["/etc/passwd", "../outside.txt", "/repo/../../outside.txt"]:
            try:
                editor.resolve(attempt)
                print(f"guard FAILED to stop {attempt}")
            except ValueError as err:
                print(f"guard: {err}")

        messages = [{"role": "user", "content": (
            "The project is in /repo. In stats.py, make average() return 0.0 for an empty "
            "list instead of crashing, and add a median() function right after average(). "
            "Keep the edits small."
        )}]
        print()
        final = run_conversation(client, messages, tools=[text_editor_schema],
                                 tracker=tracker, on_turn=show_turn,
                                 functions={TOOL_NAME: editor})
        print(f"\nClaude: {text_from(final).strip()}")

        print("\nstats.py now:\n")
        print(stats.read_text())

        # Does the edited file actually do what was asked? Run it in a separate process
        # inside the sandbox — it is model-written code, so not in this one.
        check = ("from stats import average, median, spread\n"
                 "assert average([]) == 0.0\n"
                 "assert average([1, 2, 3]) == 2\n"
                 "assert median([3, 1, 2]) == 2\n"
                 "assert median([4, 1, 3, 2]) == 2.5\n"
                 "assert spread([1, 5]) == 4\n"
                 "print('behaviour check: all assertions pass')")
        result = subprocess.run([sys.executable, "-c", check], cwd=tmp,
                                capture_output=True, text=True, timeout=10)
        print(result.stdout.strip() or f"behaviour check FAILED:\n{result.stderr.strip()}")

        print(f"\nbackups held: {len(editor.backups)} — the undo the tool no longer offers")

    tracker.report()


if __name__ == "__main__":
    run(main)
