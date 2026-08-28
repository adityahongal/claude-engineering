"""Structure with XML tags.

Tags separate the parts of a prompt that are instructions from the parts that are data, so
a long prompt stays unambiguous about which is which.
"""

from helpers import UsageTracker, compare, get_client, run

MODEL = "claude-sonnet-5"

# The data the prompt operates on, kept out of the prompt string itself. Realistic shape:
# in production this is user input or a fetched document, not something you typed.
DOCUMENT = """
"""


def main():
    client = get_client()
    tracker = UsageTracker(MODEL)

    # f-strings here — the DOCUMENT has to actually reach the prompt. A plain string sends
    # the literal text "{DOCUMENT}" and Claude answers about nothing, confidently.
    prompts = {
        "unstructured": f"",
        "tagged": f"",
    }

    compare(client, prompts, tracker=tracker)

    tracker.report()


if __name__ == "__main__":
    run(main)
