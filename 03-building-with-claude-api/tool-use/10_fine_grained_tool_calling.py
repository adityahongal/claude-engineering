"""Fine grained tool calling.

Closer control over how tool calls are produced and streamed, rather than waiting for a
complete tool_use block to arrive.
"""

# Basic Tool Streaming :-

# With streaming enabled, Claude sends back different types of events as it processes your request. 
# We're already familiar with events like ContentBlockDelta for regular text generation.
# For tool use, you'll also need to handle a new event type called InputJsonEvent.
# refer here - https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2Fa46l9irobhg0f5webscixp0bs%2Fpublic%2F1752775508%2F06_-_011.1_-_Fine_Grained_Tool_Calling_01.1752775507859.png

# Each InputJsonEvent contains two key properties:

# 1. partial_json - A chunk of JSON representing part of the tool arguments
# 2. snapshot - The cumulative JSON built up from all chunks received so far

# Here's how you handle these events in your streaming pipeline:
# for chunk in stream:
#     if chunk.type == "input_json":
#         # Process the partial JSON chunk
#         print(chunk.partial_json)
#         # Or use the complete snapshot so far
#         current_args = chunk.snapshot

# refer image - https://everpath-course-content.s3-accelerate.amazonaws.com/instructor%2Fa46l9irobhg0f5webscixp0bs%2Fpublic%2F1752775508%2F06_-_011.1_-_Fine_Grained_Tool_Calling_02.1752775508676.png

# How JSON Validation Works ??

# The Anthropic API doesn't immediately send you every chunk as Claude generates it. 
# Instead, it buffers chunks and validates them first.
# The API waits for complete "top-level key-value pairs" before sending anything. 
# For example, if your tool expects this structure:
# {
#   "abstract": "This paper presents a novel...",
#   "meta": {
#     "word_count": 847,
#     "review": "This paper introduces QuanNet..."
#   }
# }

# The API will:
# 1. Wait until the entire abstract value is complete
# 2. Validate that key-value pair against your schema
# 3. Send all the buffered chunks for abstract at once
# 4. Repeat the process for the meta object

# This validation process explains why you see delays followed by bursts of text, even with streaming enabled. 
# The chunks are being held back until a complete, valid top-level key-value pair is ready.

# Fine-Grained Tool Calling:

# If you need faster, more granular streaming 
# - perhaps to show users immediate updates or start processing partial results quickly 
# - you can enable fine-grained tool calling.

# Fine grained tool calling sends groups of chunks without waiting for a full top level key to be created
# The critical part!!!! --> JSON validation is disabled!, our could handle invalid tool inputs

# Fine-grained tool calling does one main thing: it disables JSON validation on the API side. 
# This means:

# - You get chunks as soon as Claude generates them
# - No buffering delays between top-level keys
# - More traditional streaming behavior
# - Critical: JSON validation is disabled - your code must handle invalid JSON

# Enable it by adding fine_grained=True to your API call:

# run_conversation(
#     messages, 
#     tools=[save_article_schema], 
#     fine_grained=True
# )
# With fine-grained tool calling, you might receive a word_count value much earlier in the stream, 
# without waiting for the entire meta object to be completed.

# When to Use Fine-Grained Tool Calling
# Consider enabling fine-grained tool calling when:

# - You need to show users real-time progress on tool argument generation
# - You want to start processing partial tool results as quickly as possible
# - The buffering delays negatively impact your user experience
# - You're comfortable implementing robust JSON error handling


# ─────────────────────────────────────────────────────────────────────────────────────
# DRIFT: how you switch it on has changed since the course was recorded.
#
#   course:  run_conversation(..., fine_grained=True)
#            → a client.beta call with betas=["fine-grained-tool-streaming-2025-05-14"]
#
#   now:     "eager_input_streaming": True   on each TOOL DEFINITION
#            → the ordinary client.messages.stream(...), no beta, no header
#
# It is out of beta and moved from the request to the tool, so it is per tool: one tool
# can stream eagerly while another in the same request stays buffered. Do not send the
# old beta header as well. The events are unchanged — `input_json` with .partial_json and
# .snapshot, exactly as in the notes above. Only the timing, and the validation guarantee,
# differ.
#
# The snapshot is not a progress bar. It is parsed in jiter's partial mode, which drops an
# unfinished string entirely and keeps an unfinished number as whatever digits have arrived.
# Live progress on a long string means accumulating partial_json yourself.
#
# What this file does: streams the SAME request twice — once buffered, once eager — and
# times every input_json event. The notes describe "delays followed by bursts"; here it is
# measured instead of described.
#
# What you take on when you turn it on. The API no longer validates the tool input, and
# the SDK assembles it with a TOLERANT partial-JSON parser — broken JSON often comes back
# as a quietly truncated object rather than an exception. So, in order:
#
#   1. stop_reason == "max_tokens" with a tool_use present → the input was cut off. It
#      still parses, as a valid-looking partial object. Do not run it.
#   2. validate the parsed input against the schema yourself, before running anything.
#   3. a ValueError from the stream iterator is JSON the SDK could not parse at all; it
#      comes from inside the `with` block, so that is what the try wraps.
# ─────────────────────────────────────────────────────────────────────────────────────

import time

from helpers import MAX_TOKENS, MODEL, get_client, run

# The course's example tool: two top-level keys, one of them an object. That shape is the
# point — buffering happens per TOP-LEVEL key, so `meta` cannot arrive until all of it,
# word_count and review together, is complete and validated.
save_article_schema = {
    "name": "save_article",
    "description": (
        "Save a research article summary. Call this exactly once, with the abstract and "
        "its metadata filled in."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "abstract": {"type": "string", "description": "The paper's abstract, ~150 words."},
            "meta": {
                "type": "object",
                "properties": {
                    "word_count": {"type": "integer",
                                   "description": "Number of words in the abstract."},
                    "review": {"type": "string",
                               "description": "A two-sentence critical review of the paper."},
                },
                "required": ["word_count", "review"],
            },
        },
        "required": ["abstract", "meta"],
    },
}

PROMPT = (
    "Invent a short research paper on quantum networking. Use the save_article tool to save "
    "its abstract and metadata. Call the tool right away; no commentary."
)


def validate_article(args) -> list:
    """Step 2 above. With eager streaming, nobody else checks this."""
    problems = []
    if not isinstance(args, dict):
        return [f"input is {type(args).__name__}, not an object"]
    if not isinstance(args.get("abstract"), str) or not args["abstract"].strip():
        problems.append("abstract missing or not a string")
    meta = args.get("meta")
    if not isinstance(meta, dict):
        problems.append("meta missing or not an object")
    else:
        if not isinstance(meta.get("word_count"), int):
            problems.append("meta.word_count missing or not an integer")
        if not isinstance(meta.get("review"), str):
            problems.append("meta.review missing or not a string")
    return problems


def stream_once(client, eager: bool):
    """One streamed request. Returns (final message, [(seconds, partial_json, snapshot)])."""
    tool = {**save_article_schema, "eager_input_streaming": True} if eager else save_article_schema
    events = []
    started = None   # when the tool_use block opened — the clock for every input_json

    with client.messages.stream(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        tools=[tool],
        messages=[{"role": "user", "content": PROMPT}],
    ) as stream:
        for event in stream:
            if event.type == "content_block_start" and event.content_block.type == "tool_use":
                started = time.perf_counter()
            elif event.type == "input_json":
                # snapshot is everything parsed so far — a dict, not a string.
                events.append((time.perf_counter() - started, event.partial_json,
                               event.snapshot))
        final = stream.get_final_message()

    return final, events


def describe(label, final, events):
    print(f"\n── {label} " + "─" * (70 - len(label)))
    if not events:
        print("  no input_json events — Claude did not call the tool")
        return

    gaps = [b[0] - a[0] for a, b in zip(events, events[1:])]
    print(f"  input_json events:      {len(events)}")
    print(f"  first fragment after:   {events[0][0]:.2f}s   (from the tool_use block opening)")
    print(f"  last fragment after:    {events[-1][0]:.2f}s")
    print(f"  longest silence:        {max(gaps, default=0):.2f}s")
    print(f"  biggest single chunk:   {max(len(e[1]) for e in events)} chars")

    # The honest progress measure is the RAW json, not the snapshot (see below): how much of
    # it had arrived by the halfway point of the tool call?
    total = sum(len(e[1]) for e in events)
    halfway = events[-1][0] / 2
    by_halfway = sum(len(e[1]) for e in events if e[0] <= halfway)
    print(f"  raw JSON by halfway:    {by_halfway} of {total} chars  (at {halfway:.2f}s)")

    # When did each top-level key first show up in the SNAPSHOT? Not when it started
    # arriving: the SDK builds snapshot with jiter's partial mode, which DROPS a string
    # until its closing quote arrives. So an abstract streaming in character by character
    # is invisible in snapshot until it is finished, eager or not — and a number cut
    # mid-digit shows up as a smaller, wrong number ("word_count": 1 while 12 is arriving).
    # To show a half-written string live, accumulate partial_json yourself.
    seen = {}
    for t, _, snapshot in events:
        if isinstance(snapshot, dict):
            for key in snapshot:
                seen.setdefault(key, (t, snapshot))
    for key, (t, snapshot) in seen.items():
        value = snapshot[key]
        shape = (f"{sorted(value)}" if isinstance(value, dict)
                 else f"{len(value)} chars" if isinstance(value, str) else repr(value))
        print(f"  '{key}' first seen at:  {t:.2f}s   holding {shape}")

    print(f"  stop_reason:            {final.stop_reason}")


def check(final):
    """Steps 1 and 2: what has to happen before an eager tool input is trusted."""
    tool_uses = [b for b in final.content if b.type == "tool_use"]
    if final.stop_reason == "max_tokens" and tool_uses:
        return "TRUNCATED — the input parses, but it is cut off. Not running it."
    for block in tool_uses:
        problems = validate_article(block.input)
        if problems:
            return f"INVALID — {'; '.join(problems)}"
        return (f"valid — abstract {len(block.input['abstract'].split())} words, "
                f"meta.word_count says {block.input['meta']['word_count']}")
    return "no tool call to check"


def main():
    client = get_client()

    buffered, buffered_events = stream_once(client, eager=False)
    describe("buffered (default)", buffered, buffered_events)

    try:
        eager, eager_events = stream_once(client, eager=True)
    except ValueError as err:
        # Step 3: JSON so broken the SDK's tolerant parser gave up. Raised mid-stream,
        # before the block completed, so there is no tool_use_id to answer — the only
        # recovery is to re-issue the request.
        print(f"\neager stream produced unparseable tool JSON: {err}")
        return
    describe("eager_input_streaming=True", eager, eager_events)

    print(f"\ninput check, eager:     {check(eager)}")
    print(f"input check, buffered:  {check(buffered)}")


if __name__ == "__main__":
    run(main)
