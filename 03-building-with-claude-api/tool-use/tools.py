"""The tool registry — functions, schemas, and the dispatch that runs them.

Every numbered lesson file imports from here. It lives outside the numbering because a
module name cannot begin with a digit: `from 03_tool_functions import ...` is a SyntaxError,
so a numbered file can be RUN but never IMPORTED. Anything shared has to sit in a plainly
named module.

That is a constraint, but it lands on the structure this project needs anyway. By the end
of the module there are three tools, three schemas and one dispatch, and keeping a function
next to the schema that describes it is the only guard against the two drifting apart —
nothing checks that a schema still matches its function.

Three things stay in sync here, by sitting in the same file:

    get_current_datetime          the function Claude cannot run
    get_current_datetime_schema   how Claude is told to call it
    TOOL_FUNCTIONS                name string -> callable
"""

from datetime import datetime

from anthropic.types import ToolParam


# ── the functions ────────────────────────────────────────────────────────────────────

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    """Claude has no clock. This is the tool that gives it one."""
    if not date_format:
        # Claude can read this message and retry with a valid format, so the wording is
        # part of the interface rather than a developer-only detail.
        raise ValueError("date_format cannot be empty")
    return datetime.now().strftime(date_format)


# ── the schemas ──────────────────────────────────────────────────────────────────────

# The description is not documentation — it is the entire basis on which Claude decides
# whether to call this and what to pass. Vague here is a prompt engineering bug in a JSON
# hat.
get_current_datetime_schema = ToolParam({
    "name": get_current_datetime.__name__,
    "description": (
        "Get the current date and time, formatted as a string. "
        "Use this whenever you need to know what the current date or time is, "
        "for example to timestamp something, compute a relative date, or answer "
        "a question that depends on 'now'. Returns the formatted datetime string."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "date_format": {
                "type": "string",
                "description": (
                    "A Python strftime format string controlling how the datetime "
                    "is rendered, e.g. '%Y-%m-%d %H:%M:%S' for '2026-09-01 14:30:00', "
                    "'%Y-%m-%d' for just the date, or '%H:%M' for just the time. "
                    "Defaults to '%Y-%m-%d %H:%M:%S' if omitted."
                ),
                "default": "%Y-%m-%d %H:%M:%S",
            }
        },
        # Exactly the parameters with no Python default. Too strict and Claude invents a
        # value for something that had a perfectly good default; too loose and it omits
        # an argument the function needs.
        "required": [],
    },
})

ALL_SCHEMAS = [get_current_datetime_schema]


# ── the dispatch ─────────────────────────────────────────────────────────────────────

# Claude sends a NAME, a string. Something has to turn that into something callable, and a
# dict is the whole mechanism.
TOOL_FUNCTIONS = {
    get_current_datetime.__name__: get_current_datetime,
}


def run_tool(block) -> dict:
    """Execute one tool_use block and return the tool_result block to send back.

    Every exit path returns a tool_result. Claude is blocked waiting on this id, so "the
    function raised" still has to come back as an answer — one flagged is_error=True.
    Letting the exception escape leaves a tool_use that nothing ever replied to.
    """
    function = TOOL_FUNCTIONS.get(block.name)

    if function is None:
        # Claude can ask for a tool that does not exist. Saying so is more useful than
        # crashing: it can pick a real one next turn.
        return tool_result(block.id, f"No tool named {block.name!r}", is_error=True)

    try:
        # block.input is the arguments Claude chose, as a dict; ** spreads it into keyword
        # arguments, so {"date_format": "%H:%M:%S"} becomes
        # get_current_datetime(date_format="%H:%M:%S").
        output = function(**block.input)
    except Exception as err:
        # Deliberately broad. Catching bare Exception usually hides bugs; here every
        # failure has to become a message Claude can read and retry from. A schema that has
        # drifted from its function surfaces as a TypeError right here.
        return tool_result(block.id, f"{type(err).__name__}: {err}", is_error=True)

    # content must be a STRING — a dict or an int is a 400. str() is enough for a
    # string-returning tool; anything structured needs json.dumps().
    return tool_result(block.id, str(output), is_error=False)


def tool_result(tool_use_id: str, content: str, is_error: bool = False) -> dict:
    """One tool_result block. tool_use_id is the only link back to the request."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
    }
