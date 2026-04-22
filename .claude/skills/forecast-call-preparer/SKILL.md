---
name: forecast-call-preparer
description: Prepare a SaaS AE for Monday's forecast call — commit / best case / pipeline buckets with risk flags from Gong transcripts and Salesforce activity. Use Monday morning before the 10am call.
---

# Forecast call preparer (SaaS AE)

The forecast call wants three numbers from the AE: **commit** (near-certain), **best case** (plausible with work), **pipeline** (later-quarter). Each number needs a one-line defence. This skill assembles that.

## Workflow

1. **Read the AE's open opps.** From `public/salesforce-opps.csv` (AE's personal export) — columns: opp_name, account, amount, close_date, stage, last_activity.
2. **Read the Gong activity index** from `public/gong-summaries.csv` (one row per recent call: account, date, topic, summary, sentiment signal, risks flagged).
3. **Bucket each opp** by stage + close-date fit + recent activity:
   - **Commit** — in late stage (contracting / legal), close this quarter, last-activity < 7 days, no risk flag, or flag resolved
   - **Best case** — mid stage, close plausible this quarter, active, some risk
   - **Pipeline** — early stage, or close date slipping, or risk not contained
4. **For each opp, write a one-line defence** citing the Gong summary and the last activity. Risk flags get a one-line mitigation plan.
5. **Draft `public/forecast-<yyyy-mm-dd>.md`**:
   - Commit $X on opps [A, B, C]
   - Best case $Y on opps [D, E]
   - Pipeline $Z on opps [F, G, H]
   - Quota gap vs commit
   - Top 3 risks + the action you propose for each (draft follow-up email / schedule exec call / re-scope)
6. **Post `check_in`** in the AE's goal channel. Include any drafted follow-up emails as separate artifacts they can send.

## What not to do
- Don't move an opp up a bucket to hit quota. Honest forecast > rosy forecast.
- Don't quote internal Gong sentiment scores as if they were customer-stated facts — they're signal, not truth.
