"""Tool schemas.

Describing a function to Claude: name, what it does, and its parameters as JSON Schema.
The description is not documentation, it is the only thing Claude has to decide whether
and how to call it.
"""

# After writing your tool function, 
# the next step is creating a JSON schema that tells Claude what arguments your function expects and how to use it. 
# This schema acts as documentation that Claude reads to understand when and how to call your tools.

# The complete tool specification has three main parts:

# 1. name - A clear, descriptive name for your tool (like "get_weather")
# 2. description - What the tool does, when to use it, and what it returns
# 3. input_schema - The actual JSON schema describing the function's arguments

# Adding Type Safety
# For better type checking, import and use the ToolParam type from the Anthropic library


# The schema lives in tools.py, beside the function it describes. Nothing checks that a
# schema still matches its function — keeping them in one file is the only guard there is.
# `"name": get_current_datetime.__name__` removes one drift risk outright: the advertised
# name cannot disagree with the real one.

import json

from tools import get_current_datetime, get_current_datetime_schema


def main():
    print(json.dumps(dict(get_current_datetime_schema), indent=2))

    # The check worth repeating whenever a tool is added: schema properties should match the
    # function's parameters, and "required" should be exactly the ones with no default.
    import inspect
    sig = inspect.signature(get_current_datetime)
    props = set(get_current_datetime_schema["input_schema"]["properties"])
    required = set(get_current_datetime_schema["input_schema"].get("required", []))
    no_default = {n for n, p in sig.parameters.items()
                  if p.default is inspect.Parameter.empty}

    print("\nparams match properties:", set(sig.parameters) == props)
    print("required matches no-default params:", required == no_default)


if __name__ == "__main__":
    main()
