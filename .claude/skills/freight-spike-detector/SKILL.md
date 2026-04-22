---
name: freight-spike-detector
description: Detect anomalous freight-rate changes on routes the firm ships on. Use when shipment-ops flags a cost surprise or on a scheduled weekly run.
---

# Freight spike detector

Ocean and air freight rates move weekly on container indices (SCFI, WCI, FBX) and on the forwarder quote sheet. Sudden spikes erode margin silently. This skill surfaces them early.

## Workflow

1. **Load route history.** `public/freight-rates.csv` with columns: `week_ending`, `route` (e.g. `NSA-HAM`), `mode` (sea / air), `forwarder`, `rate_usd_per_teu_or_kg`.
2. **Compute per-route statistics** with `code_exec`:
   - Rolling 8-week mean + stdev per route.
   - Latest rate z-score per route.
   - Week-over-week change.
3. **Flag** any route where:
   - |z-score| > 2, OR
   - week-over-week change > 15%, OR
   - the latest rate is the highest in the last 12 weeks.
4. **Cross-reference open shipments.** If `public/open-shipments.csv` exists, join flagged routes to open shipments so the `check_in` is actionable.
5. **Write artifact** to `public/freight-spike-<week>.md` with the flagged routes, the magnitude, affected shipments, and a one-line cause hypothesis (capacity, fuel surcharge, festival demand, etc. — stated as hypothesis, not fact).
6. **Post `check_in`** with the top 3 spikes. If a spike affects an open shipment, `goal_ask` the shipment-ops channel asking whether to re-quote or push the sailing.

## What not to do
- Don't trigger spikes on 1-week noise alone. The 12-week and z-score tests exist to filter that out.
- Don't commit to a cause in the artifact — "hypothesis:" is the right framing. The forwarder or carrier confirms.
