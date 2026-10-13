"""Token usage and estimated cost across a run.

Started as a copy of prompt-evaluation/usage_tracker.py, which stays where it is — the
earlier modules import it from there. Two additions here:

  * prompt-caching tokens. A cached request reports three input counts, billed at
    different rates: input_tokens (full price), cache_creation_input_tokens (writing the
    cache, 1.25x for the default 5-minute cache) and cache_read_input_tokens (0.1x). The
    original only counts the first, so a cached run looked cheaper than it was on the
    write and dearer than it was on the reads.
  * server-side tool calls (web search), counted from usage.server_tool_use — billed per
    call, on top of tokens, and not priced here.
"""

# Dollars per MILLION tokens. These change — check the pricing page rather than trusting
# this table. Same Sonnet 5 rate as the original tracker, which notes that the introductory
# $2 / $10 ended 2026-08-31.
PRICES = {
    "claude-sonnet-5":  {"input":  3.00, "output": 15.00},
    "claude-opus-5":    {"input":  5.00, "output": 25.00},
    "claude-opus-5-5":  {"input":  4.00, "output": 20.00},
    "claude-haiku-4-5": {"input":  1.00, "output":  5.00},
}

CACHE_WRITE = 1.25   # x the input rate, 5-minute cache
CACHE_READ = 0.10    # x the input rate


class UsageTracker:
    """Running totals of tokens and cost for one model."""

    def __init__(self, model: str):
        if model not in PRICES:
            raise ValueError(f"No price on file for {model!r}. Add it to PRICES.")
        self.model = model
        self.calls = 0
        self.input_tokens = 0
        self.cache_write_tokens = 0
        self.cache_read_tokens = 0
        self.output_tokens = 0
        self.server_tool_calls = 0
        self.truncated = 0

    def record(self, response):
        """Add one response's usage. Returns the response, so it can wrap a call inline."""
        usage = response.usage
        self.calls += 1
        self.input_tokens += usage.input_tokens
        self.cache_write_tokens += getattr(usage, "cache_creation_input_tokens", 0) or 0
        self.cache_read_tokens += getattr(usage, "cache_read_input_tokens", 0) or 0
        self.output_tokens += usage.output_tokens

        server = getattr(usage, "server_tool_use", None)
        if server is not None:
            self.server_tool_calls += getattr(server, "web_search_requests", 0) or 0

        # Cut off, not finished — easy to miss by eye.
        if getattr(response, "stop_reason", None) == "max_tokens":
            self.truncated += 1
        return response

    @property
    def cost(self) -> float:
        rate = PRICES[self.model]
        per_input = rate["input"] / 1_000_000
        return (self.input_tokens * per_input
                + self.cache_write_tokens * per_input * CACHE_WRITE
                + self.cache_read_tokens * per_input * CACHE_READ
                + self.output_tokens * rate["output"] / 1_000_000)

    def report(self) -> None:
        line = (f"{self.calls} calls | in {self.input_tokens:,} | out {self.output_tokens:,}")
        if self.cache_write_tokens or self.cache_read_tokens:
            line += (f" | cache write {self.cache_write_tokens:,}"
                     f" | cache read {self.cache_read_tokens:,}")
        if self.server_tool_calls:
            line += f" | server tool calls {self.server_tool_calls} (billed separately)"
        print(f"{line} | ~${self.cost:.4f}")
        if self.truncated:
            print(f"  !! {self.truncated} of {self.calls} responses hit max_tokens and were "
                  f"cut off. Raise max_tokens and re-run.")
