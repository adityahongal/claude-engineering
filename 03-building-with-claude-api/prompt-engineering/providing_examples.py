"""Providing examples.

Showing a worked example instead of describing the output in prose. Usually the single
biggest lever of the four, and the easiest one to get subtly wrong.
"""

from helpers import UsageTracker, compare, get_client, run

MODEL = "claude-sonnet-5"


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    # Claude copies whatever the examples demonstrate, including things you did not mean to
    # demonstrate — if every example output is one sentence long, expect one sentence.
    prompts = {
        "described": "",
        "one example": "",
        "several examples": "",
    }

    compare(client, prompts, tracker=tracker)

    tracker.report()


if __name__ == "__main__":
    run(main)
