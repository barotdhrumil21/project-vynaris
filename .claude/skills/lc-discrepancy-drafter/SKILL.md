---
name: lc-discrepancy-drafter
description: Draft a discrepancy response letter for a documentary letter of credit. Use when the bank has flagged issues on an LC presentation and the credit-risk / trade-ops team needs to reply within the cure window.
---

# LC discrepancy drafter

Indian exporters under UCP 600 get 5 banking days to cure discrepancies on a documentary LC. A clean reply needs: the LC reference, the exact bank wording, a line-by-line rebuttal with document citations, and a closing asking the bank to either waive or authorise amendment.

## Workflow

1. **Gather the LC package.** Ask which LC (by bank ref or buyer name). Use `fs_read` on files the owner maintains — typical paths:
   - `public/lc-tracker.xlsx` or `public/lc-tracker.csv` (status per LC)
   - `public/lc-docs/<lc-ref>/` (BL, commercial invoice, packing list, certificate of origin, inspection certificate)
2. **Read the bank's discrepancy notice.** Ask for the notice text or file path.
3. **Classify each discrepancy.** For each item flagged, label one of:
   - **Typo / clerical** — trivially curable by amendment.
   - **Presentation error** — we mis-filed or mis-sequenced; curable.
   - **Substantive** — document content contradicts LC terms; may need buyer consent for amendment.
   - **Bank over-reach** — not a valid UCP 600 discrepancy; rebut with the clause.
4. **Draft the letter.** Structure:
   - Addressee (issuing / advising bank)
   - Reference (our export, LC number, presentation date)
   - Point-by-point rebuttal, one paragraph per flag
   - Ask: waive / amend / reimburse
   - Our contact + signatory
5. **Save the draft** to `public/lc/<lc-ref>-discrepancy-response-<date>.md`.
6. **Post a `check_in`** to the owner's goal channel: 1 line summary + the draft's path. Include an `ask` if a buyer decision is blocking (e.g. amendment consent).

## What not to do
- Don't fabricate references to UCP 600 articles. If unsure which clause governs, call it out and ask the owner.
- Don't send the letter — hand the draft to the owner. Trade finance replies go out on letterhead.
- Don't widen scope: this is one discrepancy package, not a policy review.
