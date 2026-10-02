"""The web search tool.

A server-side tool — Anthropic runs this one, so there is no local function to write and
no tool_result to send back. Billed separately from tokens.
"""
# Important note: Your organization must enable the Web Search tool in the settings console before using it.

# Claude includes a built-in web search tool that lets it search the internet for current or specialized information to answer user questions. 
# Unlike other tools where you need to provide the implementation, 
# Claude handles the entire search process automatically - you just need to provide a simple schema to enable it.

# Setting Up the Web Search Tool

# To use the web search tool, you create a schema object with these required fields:
# web_search_schema = {
#     "type": "web_search_20250305",
#     "name": "web_search", 
#     "max_uses": 5
# }
# The max_uses field limits how many searches Claude can perform. 
# Claude might do follow-up searches based on initial results, so this prevents excessive API calls. 
# A single search returns multiple results, but Claude may decide additional searches are needed.

# How the Response Works

# When Claude uses the web search tool, the response contains several types of blocks:

# - Text blocks - Claude's explanation of what it's doing
# - ServerToolUseBlock - Shows the exact search query Claude used
# - WebSearchToolResultBlock - Contains the search results
# - WebSearchResultBlock - Individual search results with titles and URLs
# - Citation blocks - Text that supports Claude's statements

# The response structure lets you see exactly what Claude searched for and which sources it found. 
# Citations include the specific text Claude used to support its answers, along with the source URLs.

# Restricting Search Domains

# You can limit searches to specific domains using the allowed_domains field. 
# This is particularly useful when you want reliable, authoritative sources:

# web_search_schema = {
#     "type": "web_search_20250305",
#     "name": "web_search",
#     "max_uses": 5,
#     "allowed_domains": ["nih.gov"]
# }
# For example, when asking about medical or exercise advice, 
# restricting to domains like PubMed (nih.gov) ensures you get evidence-based information rather than random blog content.

# Rendering Search Results

# The different block types in the response are designed for specific UI rendering:
# - Render text blocks as regular content
# - Display web search results as a list of sources at the top
# - Show citations inline with the text, including the source domain, page title, URL, and quoted text

# This structure helps users understand how Claude arrived at its answers and provides transparency about the sources being used. 
# The citation format makes it clear which specific information came from which sources, building trust in the AI's responses.

# Practical Usage

# The web search tool works best for:
# - Current events and recent developments
# - Specialized information not in Claude's training data
# - Fact-checking and finding authoritative sources
# - Research tasks requiring up-to-date information

# Simply include the schema in your tools array when making API calls, and 
# Claude will automatically decide when a web search would help answer the user's question.

# ─────────────────────────────────────────────────────────────────────────────────────
# DRIFT: the tool version.
#
#   course:  "type": "web_search_20250305"
#   now:     "type": "web_search_20260209"   on Sonnet 5 / Opus 4.6+ / Sonnet 4.6
#
# The new version adds DYNAMIC FILTERING: before results reach Claude's context, Claude
# writes and runs code (server-side) to filter them. Fewer irrelevant pages in context,
# which is fewer input tokens — the expensive part of a search. Nothing to enable: it is
# built into the version. Do not also declare code_execution; a second sandbox confuses it.
# The old version still works, and is the only one on Vertex AI.
#
# Server-side means the loop from 08 does not apply:
#
#   client tool (08–11):  stop_reason="tool_use" → YOU run it → tool_result → call again
#   server tool (here):   Anthropic runs it, inside the same request. One call, and the
#                         response already holds the query, the results and the answer.
#
# The one way it can stop early is stop_reason="pause_turn": the server's own loop hit its
# iteration limit. Resume by sending the conversation back AS IS — the trailing
# server_tool_use block tells the API where to pick up. Adding a "continue" message is
# the wrong move.
#
# A failed search does not raise and does not set is_error. It comes back as a normal
# web_search_tool_result whose content is an error OBJECT instead of a LIST of results —
# so branch on that shape before iterating it.
#
# MEASURED, and not in the course: dynamic filtering costs you the citations. With
# _20260209 the search runs INSIDE server-side code — the filter's output comes back as an
# encrypted code_execution_tool_result — and the answer's text blocks are still split
# where citations would go, but every citations list is empty. The rendering the notes
# describe (inline citations with quoted source text) needs _20250305. So this file runs
# both versions on the same question and compares them.
#
# allowed_domains covers subdomains: "python.org" also let in test.python.org, the staging
# site, alongside docs. and discuss. — a domain list is narrower than the open web, not a
# guarantee every page is the canonical one.
#
# Billing: searches are counted in response.usage.server_tool_use.web_search_requests
# and charged per search ON TOP of tokens — and the results themselves land in the input
# tokens. max_uses is the cost cap as much as it is a behaviour setting.
# ─────────────────────────────────────────────────────────────────────────────────────

from collections import Counter

from helpers import UsageTracker, add_assistant_message, chat, get_client, run

MODEL = "claude-sonnet-5"
MAX_PAUSES = 3

def web_search_schema(version):
    return {
        "type": version,
        "name": "web_search",
        "max_uses": 3,
        # The notes' example, applied: answers about Python releases from python.org only,
        # not from whatever blog ranks first.
        "allowed_domains": ["python.org"],
    }


def ask(client, tracker, question, version):
    """One question, resuming through pause_turn. Returns every response, in order."""
    messages = [{"role": "user", "content": question}]
    responses = []
    for _ in range(MAX_PAUSES + 1):
        response = chat(client, messages, tools=[web_search_schema(version)],
                        tracker=tracker)
        responses.append(response)
        if response.stop_reason != "pause_turn":
            return responses
        # Resume: the assistant turn goes back unchanged, and NOTHING is added after it.
        add_assistant_message(messages, response)
        print(f"  (pause_turn — resuming, {len(responses)} so far)")
    raise RuntimeError(f"still paused after {MAX_PAUSES} resumes")


def render(response):
    """The notes' rendering guide: sources as a list, text with its citations inline."""
    print(f"\nblocks: {dict(Counter(b.type for b in response.content))}")

    # 1. What Claude searched for.
    for block in response.content:
        if block.type == "server_tool_use" and block.name == "web_search":
            print(f"  searched: {block.input.get('query')!r}")

    # 2. What came back — a LIST on success, an error OBJECT on failure.
    print("\nsources:")
    for block in response.content:
        if block.type != "web_search_tool_result":
            continue
        if not isinstance(block.content, list):
            print(f"  search failed: {getattr(block.content, 'error_code', block.content)}")
            continue
        for result in block.content:
            print(f"  - {result.title}\n    {result.url}")

    # 3. The answer, with each claim's citation right after it.
    print("\nanswer:\n")
    footnotes = []
    empty = 0   # text blocks split off as a cited span, but carrying no citation data
    for block in response.content:
        if block.type != "text":
            continue
        print(block.text, end="")
        if block.citations == []:
            empty += 1
        for citation in block.citations or []:
            footnotes.append(citation)
            print(f"[{len(footnotes)}]", end="")
    print()
    for n, citation in enumerate(footnotes, 1):
        quoted = " ".join(citation.cited_text.split())
        print(f"\n  [{n}] {citation.title}\n      {citation.url}\n      \"{quoted[:140]}"
              + ("...\"" if len(quoted) > 140 else "\""))
    return len(footnotes), empty


def main():
    client = get_client()
    question = ("What is the latest stable Python release, and when did the most recent "
                "Python feature release (3.x.0) come out?")

    summary = []
    for version in ("web_search_20250305", "web_search_20260209"):
        tracker = UsageTracker(MODEL)
        print(f"\n{'═' * 78}\n{version}\n> {question}")
        responses = ask(client, tracker, question, version)
        cited, empty = render(responses[-1])

        searches = sum(r.usage.server_tool_use.web_search_requests
                       for r in responses if r.usage.server_tool_use)
        print(f"\nsearches billed: {searches}  (on top of the token cost below)")
        tracker.report()
        summary.append((version, tracker.input_tokens, searches, cited, empty, tracker.cost))

    print(f"\n{'═' * 78}")
    print(f"{'version':22} {'input tok':>10} {'searches':>9} {'citations':>10} "
          f"{'empty spans':>12} {'~cost':>8}")
    for version, tokens, searches, cited, empty, cost in summary:
        print(f"{version:22} {tokens:>10,} {searches:>9} {cited:>10} {empty:>12} "
              f"{'$' + format(cost, '.4f'):>8}")


if __name__ == "__main__":
    run(main)
