"""Multi-turn conversations with tools.

Keeping the history intact across a tool call. Claude's tool_use reply has to go back in
unchanged, or the tool_result that follows refers to nothing.
"""
