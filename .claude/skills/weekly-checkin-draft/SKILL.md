---
name: weekly-checkin-draft
description: Draft the Monday-morning check-in for a single goal — what moved, what's blocked, what's next — and post it for the owner to approve. Invoked by the weekly-check-in loop or by the owner on demand.
schedule: 0 9 * * mon
scope: per_goal
---

# Weekly check-in draft

The weekly check-in is the goal's heartbeat. It doesn't need new analysis — it summarises what's already in the timeline.

## Inputs

The loop passes you the `goal_id` and `channel_id`. If invoked on demand, infer from context.

## Workflow

1. **Read the goal state.** Use `view_my_goals` to get the current KR values + targets. Note which KRs moved this week.
2. **Read the channel's last 7 days of messages** (check-ins, questions, system events, agent actions). The recent-events block of your system prompt already has a summary — use it.
3. **Draft the check-in structure** — narrative + blockers + next_steps + kr_updates.
   - **Narrative** (3–5 lines): where the goal stands, notable deltas, one honest assessment (on track / at risk / off track with reason).
   - **Blockers** (0–3 items): things preventing progress. "None" is a valid answer.
   - **Next steps** (2–4 items): what you'd propose for the week ahead, ranked.
   - **KR updates**: only include KRs that moved since last check-in.
4. **Post the check-in** via `goal_check_in`. This posts to the goal's channel as a draft from the agent.
5. **If there's a material decision needed**, post a separate `goal_ask` — don't bury it in the check-in.

## Voice

Terse, numeric, honest. No "I'm excited to report…". Lead with the number.

## What not to do
- Don't write a check-in if nothing happened in the last 7 days and the KRs haven't moved. Post a single line: "No material change this week." and return.
- Don't invent action items. Next steps should be visibly supported by current state.
