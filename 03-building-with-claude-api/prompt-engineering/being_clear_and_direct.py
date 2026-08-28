"""Being clear and direct.

Say plainly what you want done. Most weak prompts are not too short — they are ambiguous
about the task, the audience, or what a finished answer looks like.
"""

from helpers import UsageTracker, compare, get_client, run

MODEL = "claude-sonnet-5"


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    # Two wordings of the SAME request. Keep the underlying task identical between them —
    # if the second prompt also asks for something different, the comparison measures both
    # changes at once and tells you nothing about clarity.
    prompts = {
        "vague": "",
        "clear and direct": "",
    }

    compare(client, prompts, tracker=tracker)

    tracker.report()


if __name__ == "__main__":
    # No parentheses on `main` — passing the function itself, not calling it. See run().
    run(main)
