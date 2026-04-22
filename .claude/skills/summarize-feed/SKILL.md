---
name: summarize-feed
description: Produce a focused digest of what's happening across the org, bounded by what the viewer can see. Use when your person asks "what's everyone working on" or "what happened today".
---

# Summarize the feed

## Inputs
- `search_org` with relevant queries
- `view_my_goals` to anchor the viewer's context

## Output shape
Keep it to 200 words or fewer. Structure:

**In motion.** 2–3 bullets — biggest in-progress threads, with owners.
**Shipped.** 1–2 bullets — recent completions or milestones.
**Stuck.** 1–2 bullets — things blocked, why, who could unblock.
**Worth your attention.** 1 bullet — something the person specifically should weigh in on, given their goals.

## Anti-patterns
- Don't list every feed entry. Synthesize.
- Don't confuse "recent" with "important."
- Don't fake visibility — if you can't see something, say so.

## Wrap
Post the digest to `public/digest-<date>.md` and post-feed a link.
