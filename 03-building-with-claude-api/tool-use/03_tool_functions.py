"""Tool functions.

The ordinary Python functions Claude will ask you to call. Nothing special about them
yet — no decorators, no registration. They are just functions.
"""

# Tool functions 

# A tool function is a plain Python function that gets executed automatically when Claude decides it needs extra information to help a user. 
# For example, if someone asks "What time is it?", Claude would call your date/time tool to get the current time.

# Best Practices for Tool Functions
# When writing tool functions, follow these guidelines:

# - Use descriptive names: Both your function name and parameter names should clearly indicate their purpose
# - Validate inputs: Check that required parameters aren't empty or invalid, and raise errors when they are
# - Provide meaningful error messages: Claude can see error messages and might retry the function call with corrected parameters
    
# The validation is particularly important because Claude learns from errors. 
# If you raise a clear error like "Location cannot be empty", Claude might try calling the function again with a proper location value.

# Let's create a function to get the current date and time. 
# This function will accept a date format parameter so Claude can request the time in different formats:
# This function uses Python's datetime module to get the current time and format it according to the provided format string. 
# The default format gives us year-month-day hour:minute:second.


# The function itself lives in tools.py, not here. A module name cannot start with a digit,
# so `from 03_tool_functions import ...` is a SyntaxError — a numbered file can be run but
# never imported. Anything a later lesson needs has to sit in a plainly named module.
#
# For reference, this is the function this lesson writes:
#
#     def get_current_datetime(date_format="%Y-%m-%d %H:%M:%S"):
#         if not date_format:
#             raise ValueError("date_format cannot be empty")
#         return datetime.now().strftime(date_format)

from tools import get_current_datetime


def main():
    # print(), not a bare call. A notebook auto-displays the last expression in a cell; a
    # script computes the value and throws it away silently.
    print(get_current_datetime())
    print(get_current_datetime("%Y/%m/%d"))
    print(get_current_datetime("%m-%Y"))


if __name__ == "__main__":
    main()
