---
name: daily-pulse-draft
description: Daily, short-form pulse on a goal. Fires at 07:00 UTC. Only emits a message if there was channel activity in the last 24 hours; otherwise silent.
schedule: 0 7 * * *
scope: per_goal
fires_only_when: recent_activity_24h
---

# Daily pulse draft

This is a lightweight sibling of `weekly-checkin-draft`. The rule is simple: if the goal's channel has moved in the last 24 hours, say one paragraph about where it stands. Otherwise, say nothing.

## Workflow

1. Read the last 24 hours of messages in the goal's channel.
2. If there's nothing meaningful (system events only, no check-ins, questions, or artifacts), **post nothing**.
3. If there's motion, draft a 3-sentence note via `goal_check_in`:
   - What moved (the one thing)
   - Any blocker that emerged
   - One concrete next-24h step

## What not to do

- Don't summarise the full week. That's `weekly-checkin-draft`'s job.
- Don't fabricate "progress" to justify the pulse. Silent is better than performative.
