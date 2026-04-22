---
name: 8d-drafter
description: Draft an 8D problem-solving report for a customer quality complaint in automotive / manufacturing. Use when a customer raises a PPM defect and the plant needs a response in 24–72 hours.
---

# 8D drafter (automotive quality)

8D is the standard root-cause-and-corrective-action format expected by OEMs. A clean 8D has: D1 team, D2 problem description, D3 interim containment, D4 root cause, D5 permanent corrective action, D6 implementation, D7 prevent recurrence, D8 team recognition.

## Workflow

1. **Gather the complaint.** Ask for the customer 8D number or the complaint text. Look in `public/8d/` for related prior reports.
2. **Read the defect data** from `public/caq-export.csv` (CAQ/Babtec dump) — filter to the part number + defect code + date window the customer cites.
3. **Draft D1–D8** into `public/8d/<customer>-<part>-<yyyy-mm-dd>.md`:
   - D1: team (engineering, QM, production, supplier)
   - D2: concrete what/when/where/magnitude — count per batch, parts affected, customer impact
   - D3: containment actions already taken (100% sort, rework, isolated batch) + effective-from date
   - D4: root cause analysis — use 5-why; name the system weakness, not the person
   - D5: permanent corrective action — what changes: FMEA update, poka-yoke, control plan rev
   - D6: implementation plan with dates
   - D7: read-across — what other parts / lines could have the same weakness
   - D8: team acknowledgement
4. **Post the draft** as a `check_in` in the cell's channel (`#cell-<n>` or `#qm-8d-open`). `goal_ask` if any D-step needs a decision from the plant manager (e.g. line stoppage).

## What not to do
- Don't write a cause in D4 that you can't evidence. "Operator error" is rarely a root cause — keep asking why.
- Don't skip D7 (read-across). The OEM checks for it.
