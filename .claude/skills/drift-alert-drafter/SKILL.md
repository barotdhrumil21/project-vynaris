---
name: drift-alert-drafter
description: Draft a drift alert when a KR has moved materially against its target. Invoked by the drift-detector loop when a threshold is crossed. Goal is to flag fast, not to fix — one-line hypothesis + recommended next action.
schedule_interval_minutes: 360
scope: per_goal
fires_only_when: kr_drifting
---

# Drift alert drafter

The drift-detector fires when a KR has crossed a configured threshold. This skill turns the signal into a one-screen alert the owner can act on.

## Inputs

Loop passes: `goal_id`, `kr_id`, `from_value`, `to_value`, `target`, `threshold_pct`.

## Workflow

1. **Confirm the drift.** Call `view_my_goals` to see current state. If the KR has already recovered, post a one-liner "resolved" and stop.
2. **Form a one-line hypothesis.** Look at recent channel events and the workspace — is there a signal (e.g. a new cohort, a creative switch, a freight spike)? If no signal, say "no obvious cause from channel events; needs manual investigation".
3. **Draft the alert** — a `check_in` with:
   - Narrative: `KR moved X → Y ({delta}%), target Z, hypothesis: {one line}`
   - Blockers: empty unless there's a real blocker
   - Next steps: the first investigative step the owner should take
   - KR updates: yes, include the changed KR's to-value
4. **Raise a question** with `goal_ask` naming the owner, with priority `blocking` only if the drift is severe (>2× threshold) or the KR trend has been negative for 3+ consecutive periods.

## What not to do
- Don't draft a remediation plan from thin air. If you don't have evidence, the alert is just the alert.
- Don't fire on noise. If the drift is within 1 stdev of the last 4 periods, label it "within normal variance" and keep the message short.
