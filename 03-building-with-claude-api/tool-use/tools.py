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

import calendar
import json
from datetime import datetime, timedelta

from anthropic.types import ToolParam


# ── the functions ────────────────────────────────────────────────────────────────────

def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
    """Claude has no clock. This is the tool that gives it one."""
    if not date_format:
        # Claude can read this message and retry with a valid format, so the wording is
        # part of the interface rather than a developer-only detail.
        raise ValueError("date_format cannot be empty")
    return datetime.now().strftime(date_format)


# Claude is unreliable at calendar arithmetic — month lengths, leap years, what weekday a
# date lands on. This does it exactly.
DURATION_UNITS = ("seconds", "minutes", "hours", "days", "weeks", "months", "years")


def add_duration_to_datetime(datetime_str, duration=0, unit="days",
                             input_format="%Y-%m-%d %H:%M:%S"):
    """Shift a datetime by `duration` units. Negative durations go backwards."""
    if unit not in DURATION_UNITS:
        raise ValueError(f"unit must be one of {', '.join(DURATION_UNITS)}; got {unit!r}")

    try:
        start = datetime.strptime(datetime_str, input_format)
    except ValueError:
        # The default input_format matches get_current_datetime's default output, so the
        # two chain cleanly. When they don't, say exactly what failed to match.
        raise ValueError(
            f"datetime_str {datetime_str!r} does not match input_format {input_format!r}"
        ) from None

    if unit in ("months", "years"):
        # timedelta has no months: they are not a fixed length. Step the month number and
        # clamp the day, so Jan 31 + 1 month is Feb 28/29 rather than an error.
        months = duration * 12 if unit == "years" else duration
        month_index = start.month - 1 + months
        year, month = start.year + month_index // 12, month_index % 12 + 1
        day = min(start.day, calendar.monthrange(year, month)[1])
        result = start.replace(year=year, month=month, day=day)
    else:
        result = start + timedelta(**{unit: duration})

    # Weekday included because "what day is it" is usually the question — the one thing
    # Claude would otherwise have to work out itself, and get wrong.
    return result.strftime("%Y-%m-%d %H:%M:%S (%A)")


# The one tool that DOES something rather than computing an answer — the part Claude cannot
# do at all. A list stands in for a real reminder store; the point is the side effect, so
# the lesson can check afterwards that a reminder exists, not just that Claude said so.
REMINDERS = []


def set_reminder(content, timestamp):
    """Store a reminder. Returns a dict, so it exercises the json.dumps path in run_tool."""
    if not content or not content.strip():
        raise ValueError("content cannot be empty")

    try:
        # fromisoformat takes '2050-06-27', '2050-06-27 09:00:00' and '2050-06-27T09:00:00'.
        # The split drops the ' (Monday)' add_duration_to_datetime appends, so its output
        # chains straight in instead of failing on a suffix our own tool added.
        when = datetime.fromisoformat(timestamp.split(" (")[0])
    except ValueError:
        raise ValueError(
            f"timestamp {timestamp!r} is not ISO 8601, e.g. '2050-06-27 09:00:00'"
        ) from None

    if when < datetime.now():
        # Exactly the error Claude can act on: recompute the date and try again.
        raise ValueError(f"timestamp {timestamp!r} is in the past")

    reminder = {"id": len(REMINDERS) + 1, "content": content.strip(),
                "timestamp": when.strftime("%Y-%m-%d %H:%M:%S (%A)")}
    REMINDERS.append(reminder)
    return {"status": "set", **reminder}


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

add_duration_to_datetime_schema = ToolParam({
    "name": add_duration_to_datetime.__name__,
    "description": (
        "Add a duration to a datetime and return the resulting datetime with its weekday. "
        "Use this for ANY date arithmetic — 'in 3 weeks', '103 days from today', "
        "'2 months before the deadline' — rather than calculating dates yourself. "
        "To work relative to now, call get_current_datetime first and pass its result in. "
        "Returns a string like '2026-09-01 14:30:00 (Tuesday)'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "datetime_str": {
                "type": "string",
                "description": (
                    "The starting datetime, written to match input_format, "
                    "e.g. '2026-09-01 14:30:00'."
                ),
            },
            "duration": {
                "type": "integer",
                "description": (
                    "How many units to add. Negative values go back in time. Defaults to 0."
                ),
                "default": 0,
            },
            "unit": {
                "type": "string",
                "enum": list(DURATION_UNITS),
                "description": "The unit of duration. Defaults to 'days'.",
                "default": "days",
            },
            "input_format": {
                "type": "string",
                "description": (
                    "The Python strftime format datetime_str is written in. Defaults to "
                    "'%Y-%m-%d %H:%M:%S', which is get_current_datetime's default output; "
                    "use '%Y-%m-%d' for a date with no time."
                ),
                "default": "%Y-%m-%d %H:%M:%S",
            },
        },
        "required": ["datetime_str"],
    },
})

set_reminder_schema = ToolParam({
    "name": set_reminder.__name__,
    "description": (
        "Set a reminder that will notify the user at a specific date and time. "
        "Only call this once you have an exact timestamp — for anything relative "
        "('next Friday', '177 days after Jan 1st'), work it out with get_current_datetime "
        "and add_duration_to_datetime first rather than calculating it yourself. "
        "Fails if the timestamp is in the past. Returns the stored reminder as JSON."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "content": {
                "type": "string",
                "description": (
                    "What to remind the user about, written as the reminder should read, "
                    "e.g. 'Doctor's appointment'."
                ),
            },
            "timestamp": {
                "type": "string",
                "description": (
                    "When to send the reminder, in ISO 8601: '2050-06-27 09:00:00', or "
                    "'2050-06-27' for midnight. add_duration_to_datetime output can be "
                    "passed in exactly as returned."
                ),
            },
        },
        "required": ["content", "timestamp"],
    },
})

ALL_SCHEMAS = [get_current_datetime_schema, add_duration_to_datetime_schema,
               set_reminder_schema]


# ── the dispatch ─────────────────────────────────────────────────────────────────────

# Claude sends a NAME, a string. Something has to turn that into something callable, and a
# dict is the whole mechanism.
TOOL_FUNCTIONS = {
    get_current_datetime.__name__: get_current_datetime,
    add_duration_to_datetime.__name__: add_duration_to_datetime,
    set_reminder.__name__: set_reminder,
}


def check_registry() -> list:
    """Every way the four steps of adding a tool can drift apart, as a list of problems.

    Adding a tool means touching four places — function, schema, ALL_SCHEMAS,
    TOOL_FUNCTIONS — and nothing fails until Claude calls the one that was missed. This
    makes "forgot one" fail before any API call instead.
    """
    import inspect

    problems = []
    schema_names = {schema["name"] for schema in ALL_SCHEMAS}
    for name in schema_names - TOOL_FUNCTIONS.keys():
        problems.append(f"{name}: has a schema but no entry in TOOL_FUNCTIONS")
    for name in TOOL_FUNCTIONS.keys() - schema_names:
        problems.append(f"{name}: in TOOL_FUNCTIONS but its schema is not in ALL_SCHEMAS")

    for schema in ALL_SCHEMAS:
        function = TOOL_FUNCTIONS.get(schema["name"])
        if function is None:
            continue
        params = inspect.signature(function).parameters
        props = set(schema["input_schema"]["properties"])
        required = set(schema["input_schema"].get("required", []))
        no_default = {n for n, p in params.items() if p.default is inspect.Parameter.empty}
        if set(params) != props:
            problems.append(f"{schema['name']}: parameters {sorted(params)} "
                            f"!= schema properties {sorted(props)}")
        if required != no_default:
            problems.append(f"{schema['name']}: required {sorted(required)} "
                            f"!= no-default parameters {sorted(no_default)}")
    return problems


def run_tool(block, functions: dict | None = None) -> dict:
    """Execute one tool_use block and return the tool_result block to send back.

    Every exit path returns a tool_result. Claude is blocked waiting on this id, so "the
    function raised" still has to come back as an answer — one flagged is_error=True.
    Letting the exception escape leaves a tool_use that nothing ever replied to.

    `functions` overrides the registry — for tools with no schema here, like the
    Anthropic-defined text editor in 11, which still needs a local function.
    """
    function = (TOOL_FUNCTIONS if functions is None else functions).get(block.name)

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

    # content must be a STRING — a dict or an int is a 400. A string goes through as-is;
    # anything else is json.dumps()ed. The course dumps everything, but json.dumps on a
    # string wraps it in quotes: '"2026-10-01"' — harmless, and pure noise.
    content = output if isinstance(output, str) else json.dumps(output)
    return tool_result(block.id, content, is_error=False)


def run_tools(response, functions: dict | None = None) -> list:
    """A tool_result for every tool_use block in the response, in order.

    The list is the whole content of the next user message. Claude can ask for several
    tools in one reply, and each one needs its own answer in that same message.
    """
    return [run_tool(block, functions)
            for block in response.content if block.type == "tool_use"]


def tool_result(tool_use_id: str, content: str, is_error: bool = False) -> dict:
    """One tool_result block. tool_use_id is the only link back to the request."""
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
        "is_error": is_error,
    }
