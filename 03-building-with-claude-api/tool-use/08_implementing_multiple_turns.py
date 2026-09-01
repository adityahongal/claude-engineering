"""Implementing multiple turns.

The loop: call, check whether Claude wants a tool, run it, send the result, repeat until
it stops asking. stop_reason == 'tool_use' is the condition.
"""
