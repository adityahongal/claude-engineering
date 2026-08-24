"""Tracking token usage and estimated cost across a run.

Two things are available:

  * every response carries `.usage` with the EXACT tokens that call consumed — accumulate
    those to see what a run actually cost
  * `client.messages.count_tokens(...)` counts the input BEFORE sending, without running
    the model, so you can price a run in advance

Import it from a script in this folder with `from usage_tracker import UsageTracker`.
"""

# Dollars per MILLION tokens. These change — check the pricing page rather than trusting
# this table. Claude Sonnet 5 has introductory pricing of $2 / $10 until 2026-08-31, so
# the standard rate below over-estimates slightly during that window. Better that way
# round than the other.
PRICES = {
    "claude-sonnet-5":  {"input":  3.00, "output": 15.00},
    "claude-opus-5":    {"input":  5.00, "output": 25.00},
    "claude-haiku-4-5": {"input":  1.00, "output":  5.00},
}


class UsageTracker:
    """Running total of tokens and cost for one model."""

    def __init__(self, model: str):
        if model not in PRICES:
            raise ValueError(f"No price on file for {model!r}. Add it to PRICES.")
        self.model = model
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def record(self, response):
        """Add one response's usage to the totals. Returns the response so it can be
        wrapped around a call inline: `answer = tracker.record(client.messages.create(...))`
        """
        self.calls += 1
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        return response

    @property
    def cost(self) -> float:
        rate = PRICES[self.model]
        return (
            self.input_tokens / 1_000_000 * rate["input"]
            + self.output_tokens / 1_000_000 * rate["output"]
        )

    def report(self) -> None:
        print(
            f"{self.calls} calls | "
            f"in {self.input_tokens:,} | out {self.output_tokens:,} | "
            f"~${self.cost:.4f}"
        )


def estimate_input_tokens(client, model: str, messages: list, **kwargs) -> int:
    """Count the input tokens a request WOULD use, without sending it.

    Free — the model never runs. Only counts input; output length is unknown until
    Claude has written it, so budget that separately.
    """
    return client.messages.count_tokens(
        model=model, messages=messages, **kwargs
    ).input_tokens


def price(model: str, input_tokens: int, output_tokens: int) -> float:
    """One-off cost of a given token count, for back-of-envelope planning."""
    rate = PRICES[model]
    return (
        input_tokens / 1_000_000 * rate["input"]
        + output_tokens / 1_000_000 * rate["output"]
    )
