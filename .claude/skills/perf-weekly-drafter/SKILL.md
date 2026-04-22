---
name: perf-weekly-drafter
description: Draft the weekly performance-marketing summary for a DTC brand — spend, ROAS, CAC, creative health, incident flags. Use Monday morning so the perf standup has numbers, not theatre.
---

# Performance weekly drafter (DTC)

The weekly perf summary is the operator's heartbeat. It must answer: where did spend go, what did it return, which creative is dying, what's the one thing to change this week.

## Workflow

1. **Pull the sources** (the marketing ops team keeps these fresh):
   - `public/triplewhale-week.csv` — spend + blended ROAS by channel
   - `public/klaviyo-week.csv` — email revenue + welcome-flow open rate
   - `public/ad-creative-week.csv` — top + bottom 5 creatives by spend, CTR, ROAS
   - `public/cac-week.csv` — new-customer CAC by channel (Meta, TikTok, Google, Email, Organic)
2. **Compute deltas** (WoW) for each metric.
3. **Flag** creative fatigue (CTR drop > 25% WoW on spend > $1k), ROAS slip (below goal by more than 0.2), CAC spike (> 15% WoW).
4. **Draft `public/perf-week-<yyyy-mm-dd>.md`**:
   - Headline: blended ROAS + WoW delta + one-line hypothesis
   - Table: channel · spend · revenue · ROAS · WoW
   - Creative health: top 3 winners + 3 to retire (with evidence)
   - Incidents / risks — short bullets
   - Proposed change this week (one thing: reallocate, kill creative, brief new hook)
5. **Post as `check_in`** in `#perf-weekly-standup`. Update the ROAS / CAC / email-share KRs via `kr_update`. `goal_ask` in `#creative-review` if you're proposing to kill creatives or need 3 new hooks.

## What not to do
- Don't lead with Meta-attributed numbers only. Always show the blended view and note attribution spread.
- Don't change ad spend from this skill — draft the memo, let the human reallocate.
