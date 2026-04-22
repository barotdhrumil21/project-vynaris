---
name: edpms-reconciliation
description: Reconcile EDPMS (Export Data Processing and Monitoring System) shipments against export realisations. Use at month-end and when a shipment is approaching the 9-month realisation deadline.
---

# EDPMS reconciliation

RBI's EDPMS tracks every Indian export bill. Unreconciled shipments past 9 months show up as outstanding on the AD bank's dashboard and block export incentives. This skill builds the reconciliation worksheet.

## Workflow

1. **Read the latest export ledger.** Usually at `public/exports-ledger.csv` or `public/edpms-export.csv`. Columns expected: `shipping_bill_no`, `sb_date`, `buyer`, `invoice_value_usd`, `realised_usd`, `realised_date`, `bank_ref`.
2. **Read the EDPMS portal dump** if available — CSV export from the bank's portal, at `public/edpms-bank-<month>.csv`.
3. **Match** by shipping-bill number. For unmatched entries, classify:
   - **Realised but unlinked** — bank got funds, didn't map to the SB.
   - **Outstanding < 6 months** — on track.
   - **Outstanding 6-9 months** — warn.
   - **Outstanding > 9 months** — RBI violation; raise to CFO + admin.
4. **Compute metrics.**
   - Total outstanding (USD + INR at spot)
   - Count of bills over 9 months
   - Per-buyer breakdown
5. **Write artifact** to `public/edpms-reconciliation-<month>.md`: the table + summary + the > 9-month list with buyer + value.
6. **Post `check_in`** with the 9-month count and the total outstanding. If > 9-month count > 0, add a `goal_ask` to the compliance channel naming the buyers and asking for a plan.
7. **Update the relevant KR** (Zero EDPMS > 90d, or DSO) with `kr_update`.

## What not to do
- Don't assume missing rows mean "realised and unrecorded" — they could be unrealised. Ask before celebrating.
- Don't recommend export-advance adjustments; that's a bank / auditor decision.
