"""Prompt caching.

Reusing the work of processing a long, unchanging prompt prefix across requests. Cache
reads are billed at a fraction of normal input — when the prefix actually matches.
"""
