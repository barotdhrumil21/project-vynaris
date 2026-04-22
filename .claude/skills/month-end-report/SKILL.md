---
name: month-end-report
description: Compile a month-end report for a single goal — where the KRs landed, what got shipped, what's rolling into next month. Invoked by the month-end loop on the last business day.
schedule: 0 17 * * *
scope: per_goal
fires_only_when: last_business_day
---

# Month-end report

Month-end is not the same as a weekly check-in — it's the accounting close for the goal. It reads the full month, not the past week, and produces a written artifact in addition to the channel post.

## Workflow

1. **Read the KR history.** Scan the channel's `kr_value_changed` system events for the month. Plot (in prose) the trajectory per KR.
2. **Compile the artifact** to `public/month-end/<goal-slug>-<YYYY-MM>.md`:
   - **Outcome**: one line — hit / missed / partial, with the number.
   - **KR landing**: table — KR · start of month · end of month · target · delta.
   - **Shipped this month**: check-ins authored, artifacts produced (with paths), policy changes / decisions.
   - **Carry-over**: what's rolling into next month, with a one-line reason.
   - **Retrospective (one paragraph)**: what worked, what didn't, what we'd change. Honest.
3. **Post a `check_in`** with a one-line summary + link to the artifact. Update the KR values via `kr_update` if the final month-end numbers differ from the current value (e.g. manual-only KRs).
4. **If the goal ended this month** (deadline hit or target achieved), close it via `close_goal` with the artifact path as the close note.

## What not to do
- Don't re-analyse. Month-end is a summary of what already happened; the analysis should already live in the timeline.
- Don't write the artifact into the owner's `private/` — it's a management record. Goes in `public/month-end/`.
