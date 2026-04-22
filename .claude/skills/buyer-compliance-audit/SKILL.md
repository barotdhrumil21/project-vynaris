---
name: buyer-compliance-audit
description: Audit a buyer account against the firm's compliance requirements (KYC, sanctions, OFAC / EU lists, past payment behaviour). Use before extending credit, raising limits, or onboarding a new buyer.
---

# Buyer compliance audit

Before we extend credit to a buyer, compliance has to be current. This skill compiles the audit package in a form the credit committee can vote on in < 10 minutes.

## Workflow

1. **Identify the buyer.** Ask by name if not given. Find their folder: `public/buyers/<buyer-slug>/`.
2. **Check KYC currency.** Expected files:
   - `kyc-packet.pdf` or `.md` (constitution docs, GST, PAN, beneficial ownership)
   - `kyc-reviewed-on` annotation — if > 12 months old, flag for refresh
3. **Screen against sanctions lists** using the local copy at `public/compliance/sanctions-snapshot.csv` (legal updates this monthly). Match on legal entity name + beneficial owners.
4. **Payment behaviour.** Read the AR ledger `public/ar-ledger.csv`; compute:
   - Average days past due over last 12 months
   - Largest single delay
   - Outstanding today
5. **Past discrepancies.** Check `public/lc/` for this buyer — count of LC discrepancies in last 12 months + average days to cure.
6. **Write the audit artifact** to `public/buyers/<slug>/compliance-audit-<date>.md`. Structure:
   - **Recommendation** (one line: "Approve / Conditional / Reject")
   - **Summary** (4–6 lines, one per dimension)
   - **Evidence** (file references, dates, data)
   - **Risks and mitigations** (explicit)
7. **Post `check_in`** in the buyer's channel with the recommendation. `goal_ask` the compliance channel only if there is a blocking issue (sanctions hit, KYC > 24 months old).

## What not to do
- Don't grade the buyer's creditworthiness — that's the credit committee with financials. This is pure compliance posture.
- Don't move the sanctions snapshot; it's legal's file. If stale (> 30 days), post a question, don't fix silently.
