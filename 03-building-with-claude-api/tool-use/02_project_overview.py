"""Project overview.

What the module builds, and which tools it needs. Notes lesson — the code starts in
tool_functions.py.
"""

# We're going to build a practical project that teaches Claude how to set reminders for future dates
# The goal is straightforward: we want to be able to tell Claude "Set a reminder for my doctor's appointment. 
# It's a week from Thursday" and have Claude respond with "OK, I will remind you." 
# But to make this work, we need to address some limitations in how Claude handles time and reminders.

# Why This Is Challenging
# While Claude knows the current date, there are three specific problems we need to solve:

# Limited time awareness: Claude might know the current date, but not the exact time
# Date calculation issues: Claude doesn't always handle time-based addition well, especially when looking many days into the future
# No reminder capability: Claude doesn't know how to set a reminder - it has no built-in mechanism for this

# Each of these limitations represents a gap between what Claude can do naturally and what we need for our reminder system. 
# Tools are how we bridge these gaps.

# Tools We Need

# We'll create three separate tools to handle each challenge:
# - Get the current date time: Claude needs to know the current date and time precisely
# - Add duration to date time: Claude isn't perfect with date time addition, so we'll give it a reliable tool for this
# - Set a reminder: We need a way to actually set a reminder in the system

#  By the end, Claude will be able to handle natural language requests like "remind me in a week"
# by combining these tools to calculate the exact time and set the reminder


# ─────────────────────────────────────────────────────────────────────────────────────
# Why this project needs a LOOP, not a single tool call.
#
# "Set a reminder for my doctor's appointment, a week from Thursday" cannot be answered by
# one tool. The tools chain, and each one needs the answer from the one before it:
#
#   "a week from Thursday"
#          ↓
#   get_current_datetime()            → today's date          (Claude has no clock)
#          ↓
#   add_duration_to_datetime(...)     → the target timestamp  (Claude is unreliable at
#          ↓                                                   date arithmetic)
#   set_reminder(timestamp, text)     → done
#          ↓
#   "OK, I will remind you."
#
# Three round trips to the API, not one. Claude cannot ask for step 2 until it has seen the
# result of step 1, because the second call's arguments depend on the first call's output.
#
# That is the whole reason "Implementing multiple turns" is its own lesson: a single
# request-and-reply cannot express this. The loop is the feature.
#
# The three tools are also a deliberate split of one job into pieces Claude is bad at
# (knowing the time, doing date arithmetic) and pieces it cannot do at all (writing to a
# reminder store). That is the general rule for deciding what deserves a tool.
# ─────────────────────────────────────────────────────────────────────────────────────