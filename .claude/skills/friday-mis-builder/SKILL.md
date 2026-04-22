---
name: friday-mis-builder
description: Build the Friday MIS (management-information-summary) for a trading firm — exports, collections, LC status, freight, EDPMS aging, top buyers. Run on Thursday evening so the MD has it Friday morning.
---

# Friday MIS builder

Trading firms live by their weekly MIS. The pattern is stable: one page, same shape every week, freshest numbers Thursday evening. This skill assembles it.

## Data sources expected

| Section | File | Columns |
|---|---|---|
| Exports this week | `public/exports-ledger.csv` | shipping_bill_no, sb_date, buyer, invoice_value_usd |
| Collections this week | `public/collections.csv` | bank_ref, received_date, buyer, amount_usd |
| Open LCs | `public/lc-tracker.csv` | lc_ref, buyer, opened, expiry, value_usd, stage |
| Freight | `public/freight-rates.csv` | week_ending, route, rate |
| EDPMS outstanding | `public/edpms-outstanding.csv` | sb_no, buyer, sb_date, invoice_value_usd, days_outstanding |
| Top buyers YTD | computed from exports-ledger |

## Workflow

1. **Read all the files above.** Missing files: skip that section with a clear "source not available" note.
2. **Compute the sections.**
   - Exports this week: count, total USD, top 3 buyers
   - Collections this week: total USD, % of invoiced-this-week (book-to-cash ratio)
   - Open LCs by stage (opened, presented, paid, expiring-next-week)
   - Freight: top 3 routes by spend, week-over-week change
   - EDPMS: count of >90 day bills, total USD, top buyer exposure
   - Top buyers YTD: top 5 by invoiced USD, with outstanding %
3. **Write `public/mis/<YYYY-MM-DD>-mis.md`** in a tight 1-page format. One short paragraph narrative at the top. No prose prose — bullets and tables.
4. **Post the MIS** as a `check_in` in the #friday-mis channel. Link to the artifact. Update the relevant KRs (e.g. clean-LC rate, DSO, exports-this-week count).
5. **Raise questions** as `goal_ask` only for material exceptions (EDPMS > 90d count jumped, a collection fell through, an LC slipped stages negatively).

## What not to do
- Don't restate last week's numbers in prose — the table is the source of truth.
- Don't merge weeks. If a file's data is stale, flag it; don't patch it from memory.
