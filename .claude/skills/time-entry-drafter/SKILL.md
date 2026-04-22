---
name: time-entry-drafter
description: Draft billable time entries for a law firm associate or partner by cross-referencing their calendar, document edits, and matter-channel activity. Use Friday afternoon (or at month-end) so the attorney can submit clean entries into Elite or 3E.
---

# Time entry drafter (law firm)

Time gets lost between Elite submissions. This skill reconstructs it from signals the attorney's workspace already has.

## Workflow

1. **Pick the time window.** Ask: this week, last week, or the full month.
2. **Gather signals** (read each if present):
   - `public/calendar-<yyyy-mm>.csv` — attorney's Outlook export (start, end, subject, attendees, location)
   - `public/netdocs-edits-<yyyy-mm-dd>.csv` — NetDocuments metadata dump (doc path, matter, revision count, minutes-open)
   - Matter channel activity: list messages the attorney authored in any `#matter-*` channel in the window
3. **Bucket each time block to a matter.** Use the matter code in the calendar subject, doc path, or channel. If unclear, label "unassigned — attorney review".
4. **Assign a task description** per block, pulled from the calendar subject or the doc title. Never invent work.
5. **Produce the draft** as `public/time-entries-<yyyy-mm-dd>.md`:
   - By day, by matter, with hours (rounded to 0.1), narrative, billable flag
   - Unassigned block at the end for the attorney to manually bucket
   - Totals by matter + totals billable vs non-billable
6. **Post as `check_in`** in the attorney's agent channel. Don't push to Elite — the attorney submits.

## What not to do
- Don't round up. The attorney's realisation depends on honest entries.
- Don't guess matter codes; leave them `???` for human triage.
- Don't include confidential client names in the public feed — the draft stays in the attorney's workspace and is linked, not pasted, to channels.
