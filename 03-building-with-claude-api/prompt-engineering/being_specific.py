"""Being specific.

Constraints the answer has to satisfy — format, length, what to leave out, what to do at
the edges. Vague instructions leave Claude to pick, and it will pick differently each run.
"""

from helpers import UsageTracker, compare, get_client, run

MODEL = "claude-sonnet-5"


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    # Add one constraint at a time rather than rewriting the prompt wholesale — that way
    # you can see which constraint did the work.
    prompts = {
        "unconstrained": "",
        "specific": "",
    }

    compare(client, prompts, tracker=tracker)

    tracker.report()


if __name__ == "__main__":
    run(main)
