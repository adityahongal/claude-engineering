"""Handling message blocks.

Reading a reply that contains a tool_use block. response.content is a list, blocks carry
a type, and a single reply can hold text and tool_use together.
"""
