# Vynaris — Target Customer Profiles & User Stories

> **Living document.** This is Vynaris's north-star UX reference. Every data model decision, visibility rule, goal primitive, and agent behavior is stress-tested against the three archetype orgs below. Expand and revise as we learn from real customers.
>
> **How to use this doc when designing:**
>
> 1. Pick a proposal ("add feature X", "change primitive Y").
> 2. Walk through each of the three archetypes — does it work at their depth, their headcount, their confidentiality rules, their rhythms?
> 3. If it fails in one of them, you either narrow scope or rethink. "Works for the founder of a 10-person startup" is **not** enough.
>
> **What this doc covers:** the three starter archetypes, their realistic org depth, the roles that actually exist (by level), representative people and the kind of goals they'd set, and the Vynaris-specific design implications.
>
> **What this doc does not yet cover** (open for future expansion): healthcare orgs, agencies/consultancies, B2C retail chains, government, universities, multi-country orgs, holding-company structures. Add sections as we meet customers in these segments.

---

## Archetype summary

| # | Archetype | Location | Headcount | Industry |
|---|---|---|---|---|
| 1 | **Sanghavi Impex** | Mumbai, India | ~180 | B2B · Trading + Import/Export (textile exports, specialty chemical imports) |
| 2 | **Schäfer Präzision GmbH** | Baden-Württemberg, Germany | ~650 | B2B · Tier-1 automotive supplier (precision machined components) |
| 3 | **Barrett & Lang LLP** | Midtown NYC | ~580 (380 attorneys + 200 business pros) | B2B · Mid-BigLaw full-service firm (professional services) |
| 4 | **Nimbus Analytics** | NYC + remote US | ~200 | B2B · Series C SaaS product company (cloud data platform, $35M ARR) |
| 5 | **Luma** | LA | ~120 | B2C · DTC skincare brand (Shopify + Sephora, $45M rev) |

Picks are deliberate: span the 50–5000 range, span geography (India / Germany / US), span industry structure (distribution · production · professional services · tech product · consumer product), span GTM motion (ops-centric / manufacturing / billable-hours / enterprise-sales / performance-marketing). Together they cover the major shapes Vynaris will meet in the wild.

---

## Persona 1 — Sanghavi Impex Pvt Ltd

**Mumbai · ~180 people · ₹900 Cr revenue · textile exports + specialty chemical imports**

### Cultural context: the Indian designation ladder

Indian companies run **deep** ladders — designation inflation is real and load-bearing. Promotions happen across 8–12 distinct grades even in mid-sized firms. A 180-person trading house will use 6–7 of these levels actively.

```
CXO ─ MD / COO / CFO
 │
 ├─ President / VP
 │
 ├─ GM (General Manager)
 │
 ├─ DGM (Deputy GM)
 │
 ├─ AGM (Asst GM)
 │
 ├─ Sr. Mgr
 │
 ├─ Manager
 │
 ├─ Dy. Mgr / Asst Mgr
 │
 ├─ Sr. Executive / Sr. Officer
 │
 └─ Executive / Officer / Trainee
```

Promotions happen every 2–4 years. **AGM/DGM/GM are power levels** — most org decisions actually happen here, not at VP/CXO.

### Headcount by level (~180 total)

| Level | Roles / titles at this level | Headcount |
|---|---|---|
| **L0 — CXO** | Chairman (promoter), MD (promoter's son / outside pro), COO, CFO | 3 |
| **L1 — VP / GM** | VP-Exports, VP-Imports, GM-Operations, GM-Finance, GM-Compliance, GM-HR/Admin | 5 |
| **L2 — DGM / AGM** | Heads of specific desks/functions reporting to L1 | 8–10 |
| **L3 — Sr. Manager / Manager** | Function leads — EU Desk Manager, Procurement Manager, Logistics Manager, Docs Manager, AR Manager, Forex Manager, QC Manager | 12–15 |
| **L4 — Dy. Manager / Asst Manager** | Sub-function runners — Sr. Merchandiser, Asst Mgr Shipping, Asst Mgr Docs | 20–25 |
| **L5 — Sr. Exec / Sr. Officer** | ICs with domain depth — Sr. Merchandiser, Sr. Docs Exec, Sr. Accounts Exec | 40–50 |
| **L6 — Executive / Officer / Trainee** | Entry — Jr. Merchandiser, Docs Exec, Accounts Exec, Asst QC, Trainees | 50–60 |
| **L7 — Support** | Peons, housekeeping, drivers, warehouse helpers, clerks | 30–40 |

### Departments (ops-centric, finance-heavy)

1. **Promoter / MD office** (Chairman + MD + CFO + COO)
2. **Sales & BD — Exports** (country-wise desks: EU, US, GCC)
3. **Sales & BD — Imports / Domestic distribution**
4. **Merchandising** (specific to textile export — translation layer between buyer specs and factory execution)
5. **Procurement — raw materials & imports**
6. **Logistics & Shipping** (freight forwarding, customs liaison)
7. **Export Documentation & Compliance** (DGFT / DGCI&S / GST / FEMA / RBI filings — its own team)
8. **Finance & Accounts** (AR heavy — buyers pay on LC / 60–90-day terms; AP to factories; forex)
9. **Quality Control** (pre-shipment QC, buyer-rep coordination)
10. **HR & Admin**
11. **IT** (small — 3–5 people running Tally / SAP B1 / Oracle NetSuite + EDI)

### Merchandising deep tree — the heart of a textile export house

```
VP - Exports (L1)
 │
 ├─ DGM - Europe Desk (L2)
 │   │
 │   ├─ Sr. Manager - H&M Account (L3)
 │   │   │
 │   │   ├─ Manager - Knits Category (L3/L4)
 │   │   │   │
 │   │   │   ├─ Sr. Merchandiser - Ladies Knits (L5)
 │   │   │   │   ├─ Merchandiser - Tops (L5/L6)
 │   │   │   │   │   └─ Jr. Merchandiser - Tops (L6)
 │   │   │   │   └─ Merchandiser - Bottoms (L5/L6)
 │   │   │   │       └─ Jr. Merchandiser - Bottoms (L6)
 │   │   │   └─ Sr. Merchandiser - Mens Knits (L5)
 │   │   │
 │   │   └─ Manager - Wovens Category (L3/L4)
 │   │
 │   ├─ Sr. Manager - Zara Account (L3)
 │   └─ Manager - Other EU Buyers (L3)
 │
 ├─ DGM - USA Desk (L2)
 │   └─ Sr. Mgr - Walmart / Target / Macy's Accounts (L3)
 │
 └─ AGM - GCC Desk (L2)
```

**Span of control:** 3–6 direct reports at each level. A Sr. Manager running a single H&M account easily has **12–18 people** end-to-end when you include QC liaison, sampling assistants, and account-linked doc executives.

### Docs & Compliance deep tree (10-person team)

```
GM - Compliance & Finance (L1)
 │
 ├─ Manager - Export Documentation (L3)
 │   ├─ Asst Manager - LC Docs (L4)  ← LC banks only
 │   │   ├─ Sr. Docs Exec (L5)
 │   │   └─ Docs Exec (L6)
 │   ├─ Asst Manager - Shipping Docs (L4)  ← SB, BoL, COO, packing lists
 │   │   ├─ Sr. Docs Exec (L5)
 │   │   └─ Docs Exec (L6)
 │   └─ Asst Manager - Buyer Docs (L4)  ← buyer-specific forms, Form-A / EUR1
 │       └─ Docs Exec (L6)
 │
 └─ Compliance Officer (L3)
     ├─ Sr. Exec - DGFT / RoDTEP / MEIS (L5)
     ├─ Sr. Exec - RBI EDPMS (L5)
     └─ Exec - GST / IGST Refunds (L6)
```

### Representative people & goals

#### Priya Menon — Jr. Merchandiser, H&M Ladies Knits Tops (L6, 6 months in)
- **Responsibilities:** Track tech-pack revisions, maintain trim card, chase factories for sample submissions, update merchandising tracker daily.
- **Daily reality:** WhatsApp groups with factory, constant pings from Sr. Merchandiser, chasing QC for approval.
- **Goals:**
  - "Zero missed follow-ups on my 9 active styles"
  - "Update merchandising tracker before EOD"
  - "Sample approval turnaround ≤ 7 days"
- **Who sees her goals:** self + Sr. Merchandiser + Manager-Knits (3 levels up).

#### Arjun Patel — Sr. Merchandiser, Ladies Knits (L5, 6 yrs)
- **Responsibilities:** Owns a style end-to-end (tech-pack → FOB dispatch). Negotiates with 4–5 factories. Mentors 2 juniors.
- **Goals:**
  - "On-time shipment ≥ 97% across my 30 styles this season"
  - "First-pass sample acceptance ≥ 72%"
  - "Cost-price variance ±2% vs buyer LOI"
  - "Develop Priya to handle styles solo by Q3" *(development KR for a report)*

#### Rohan Kapoor — Sr. Manager, H&M Account (L3, 12 yrs)
- **Responsibilities:** P&L for H&M account. Monthly Buyer Business Review (BBR). Allocates orders across 4 factories. Keeps 18-person team moving.
- **Goals:**
  - "H&M revenue ≥ ₹110 Cr this FY"
  - "Maintain H&M 'A' grade on buyer scorecard" *(URL → buyer portal)*
  - "OTIF ≥ 96% across all H&M styles" *(workspace file — tracker export)*
  - "Zero compliance reject from H&M factory audit" *(binary milestone)*

#### Anita Desai — Asst Manager, LC Docs (L4, 7 yrs)
- **Responsibilities:** Every LC negotiation with SBI / ICICI / Axis. Resolves discrepancy letters. Knows the 20+ clauses that trip Indian exports.
- **Goals:**
  - "Clean LC negotiation rate ≥ 85% on my desk" *(industry average is ~60% — stretch goal)*
  - "Zero LC expiry incidents" *(binary)*
  - "Discrepancy resolution ≤ 48h" *(workspace file log)*
- **Agent leverage:** drafting discrepancy responses, verifying doc sets before submission.

#### Vikram Singh — VP Exports (L1, 22 yrs)
- **Responsibilities:** Strategy across EU/US/GCC desks. Quarterly reviews with MD. Lateral partner visits to 10 buyers/year.
- **Goals:**
  - "Total export revenue ≥ ₹650 Cr"
  - "Top-3 buyer concentration < 55%"
  - "Add 2 new EU retailers this FY"
  - "Reduce average DSO to 68 days" *(cross-function with finance)*

### How they work today
- WhatsApp groups per buyer, per shipment. Literally.
- Tally / SAP B1 / NetSuite for accounts; separate Excel trackers for shipments.
- Email threads with buyers / banks / CHAs (Customs House Agents).
- DGFT / ICEGATE portals for filings — compliance team lives there.
- Weekly MIS meeting ("Monday review") — MD reads shipment tracker, AR ageing, pipeline.

### Vynaris implications from Sanghavi Impex
- **Deep org tree imported at onboarding** with 6 distinct levels (L0–L6, ignore L7 support).
- **Matrix relationships required:** Anita (LC Docs, L4) functionally reports to Manager-Docs but also serves every buyer account — she needs visibility to H&M/Zara/Walmart account channels even though her manager isn't in them.
- **Cascade reflects (not invents) hierarchy:** when a goal is created at L3, UI should offer "also create matching goals for each direct report?"
- **Goal volume:** a VP has 4–6 active goals; an L3 Manager has 8–12; an L5/L6 exec has 3–5 narrow ones. Personal "my goals" dashboard must scale past 10 items cleanly.

---

## Persona 2 — Schäfer Präzision GmbH

**Baden-Württemberg · ~650 people · €160M revenue · IATF 16949 certified Tier-1 auto supplier**

### Cultural context: the three parallel ladders

German manufacturers have **three parallel ladders** — office/admin, production (Meister tradition), engineering (Ingenieur tradition). They don't interconvert cleanly.

```
 OFFICE                  PRODUCTION             ENGINEERING (Entwicklung)
 ──────                  ──────────             ────────────────────────
 Geschäftsführer         Werkleiter             Entwicklungsleiter / CTO
  │                        │                      │
 Prokurist                Fertigungsleiter       Leiter F&E (Abt.-Leiter Entw.)
  │                        │                      │
 Bereichsleiter           Meister                Gruppenleiter Entwicklung
  │                        │                      │
 Abteilungsleiter         Schichtführer          Senior Ingenieur
  │                        │                      │
 Gruppenleiter            Vorarbeiter            Ingenieur
  │                        │                      │
 Teamleiter               Facharbeiter           Junior Ingenieur
  │                        │                      │
 Sachbearbeiter /         Anlagenbediener /      Werkstudent / Praktikant
 Referent                 Maschinenführer
  │
 Azubi (Ausbildung)
```

**Key cultural facts:**
- **Prokurist** — legal status granted by the company, allowing signature authority within limits. Typically goes to trusted Abteilungsleiter / Bereichsleiter. Shows up on business cards; carries real weight.
- **Meister** — a 3-year vocational qualification on top of an Ausbildung. A production Meister is a *respected peer* of an Ingenieur, not a subordinate. Some earn more than young engineers.
- **Ausbildung** — 3–3.5-year apprenticeship program. Azubis work 60–70% in the plant, 30–40% at Berufsschule. A 650-person plant has 25–40 Azubis at any time (Industriemechaniker, Zerspanungsmechaniker, Industriekaufmann, Mechatroniker tracks).
- **Works Council (Betriebsrat)** — elected by employees. For ~650 people, ~9–11 members, some full-time. **Co-decides** on anything touching employees (monitoring, schedules, new software, dismissals). This is the single biggest cultural factor for a Vynaris sale in Germany.

### Headcount by level (~650 total)

| Level | Office | Production | Engineering | Azubis |
|---|---|---|---|---|
| **L0 — Geschäftsführer** | 2 (CEO + CFO, often family) | — | — | — |
| **L1 — Prokurist / Bereichsleiter** | 3–4 (CSO, COO, CTO, HR-lead) | — | — | — |
| **L2 — Abteilungsleiter** | 8–10 (Vertrieb, Einkauf, Controlling, IT, HR, QM, Logistik, Kundenservice) | 2 (Werkleiter · Fertigungsleiter) | 2–3 (Leiter Entw. · Leiter Konstr. · Leiter Test/Validierung) | — |
| **L3 — Gruppenleiter / Meister / Sr. Ing.** | 12–18 | 8–12 Meister (one per cell/line) | 8–10 Sr. Ing. / GrL | — |
| **L4 — Teamleiter / Schichtführer / Ing.** | 15–20 | 18–24 Schichtführer (3 shifts × 6–8 lines) | 15–20 Ing. | — |
| **L5 — Sachbearbeiter / Vorarbeiter / Jr. Ing.** | 40–55 Sachbearbeiter | 30–40 Vorarbeiter | 8–12 Jr. Ing. | — |
| **L6 — Facharbeiter / Anlagenbediener** | — | 200–240 Facharbeiter + 120–160 Anlagenbediener | — | 30–40 Azubis |

Rough total: ~100 office · ~430 production · ~60 engineering · ~35 apprentices · ~25 Geschäftsführung + execs + misc.

### Departments

1. **Geschäftsführung** (MDs — often 2–3: family + professional)
2. **Vertrieb / Key Account Management** (per OEM — "Bosch AM", "ZF AM", "Porsche AM")
3. **Entwicklung / R&D / Konstruktion** (mechanical engineers, FEA, prototyping)
4. **Produktion** (Fertigung — CNC, milling, assembly cells; shift leads)
5. **Qualitätsmanagement (QM)** — huge in German auto; often reports to GF directly
6. **Arbeitsvorbereitung (AV)** — production planning / scheduling
7. **Einkauf** (Procurement — steel, alloys, consumables, subcontractors)
8. **Logistik / SCM** (warehouse, inbound, inter-plant, outbound to OEM)
9. **Instandhaltung** (Maintenance — critical for OEE)
10. **Finanzen & Controlling** (cost accounting serious; Kostenstelle per cell)
11. **Personal (HR)** — heavy Works Council + Ausbildung involvement
12. **IT / Digitalisierung** — small team, runs ERP (SAP S/4 or proAlpha) + MES

### Production deep tree (~390 people)

```
Werkleiter (L2)
 │
 ├─ Fertigungsleiter (L2)
 │   │
 │   ├─ Meister Fertigungszelle 1 - Valve Bodies (L3)
 │   │   ├─ Schichtführer Frühschicht (L4)
 │   │   │   ├─ Vorarbeiter CNC 1-4 (L5)
 │   │   │   │   └─ 4-6 Facharbeiter/Anlagenbediener each
 │   │   │   └─ Vorarbeiter Montage (L5)
 │   │   ├─ Schichtführer Spätschicht (L4)  (evening, same structure)
 │   │   └─ Schichtführer Nachtschicht (L4)  (skeleton crew)
 │   │
 │   ├─ Meister Fertigungszelle 2 - Steering Components (L3)
 │   ├─ Meister Fertigungszelle 3 - EV Components (L3, ramping up)
 │   └─ Meister Montage & Endprüfung (L3)
 │
 ├─ Leiter Instandhaltung / Maintenance (L2)
 │   ├─ Meister Instandhaltung (L3)
 │   │   └─ 8-10 Facharbeiter (electricians, mechanics)
 │   └─ Gruppenleiter Predictive Maintenance (L3)
 │       └─ 3-4 Ing. + Techniker
 │
 └─ Leiter Arbeitsvorbereitung / Planning (L2)
     ├─ Gruppenleiter AV (L3)
     └─ 6-8 Sachbearbeiter AV (L5)
```

A single Meister runs a cell (~40 people across 3 shifts). **The Meister owns the OEE of that cell** end-to-end. Their daily 08:00 Shopfloor-Meeting (SFM) sets the day.

### Quality deep tree (~25 people)

Quality is disproportionately senior in German auto — OEMs audit heavily.

```
QM-Leiter / Head of Quality (L2, often Prokurist)
 │
 ├─ Gruppenleiter Lieferantenqualität (L3) — supplier quality
 │   └─ 4-5 Ing. / Sachbearbeiter SQ
 │
 ├─ Gruppenleiter Prozessqualität (L3) — process quality, CAQ, audits
 │   └─ 5-6 Ing. / Sachbearbeiter
 │
 ├─ Gruppenleiter Kundenqualität (L3) — customer quality, 8D, PPM
 │   └─ 4-5 Ing. / Sachbearbeiter (one per major customer)
 │
 └─ Messraum-Leiter (L3) — metrology lab
     └─ 3-4 Messtechniker
```

### Representative people & goals

#### Thomas Bauer — Anlagenbediener, CNC-Bereich 1 Frühschicht (L6, 14 yrs, Facharbeiter)
- **Responsibilities:** Run CNC machines. Basic maintenance. Log output. Escalate scrap.
- **Goals (reality):** he doesn't have individual goals — he's measured against the cell target. His Vorarbeiter posts the numbers. Vynaris should treat him as a **watcher**, not an owner.

#### Stefan Huber — Vorarbeiter, Montage Zelle 1 Frühschicht (L5, 20 yrs, Meisterprüfung in progress)
- **Responsibilities:** 6 Facharbeiter, assembly station. First response on line stops. Shift handover to Spätschicht.
- **Goals:**
  - "Linientakt 42 Sek. einhalten" *(takt time)*
  - "Zero missed shift-handover meetings"
  - "Second assembler trained on new station by Q2"

#### Andrea Weiss — Meister, Fertigungszelle 1 Valve Bodies (L3, 11 yrs)
- **Responsibilities:** Cell OEE across 3 shifts. Daily 08:00 SFM. Coordinates with Instandhaltung, QM, AV. Owns 8Ds for her cell.
- **Goals:**
  - "OEE Zelle 1 ≥ 82% (7-Tage rollierend)" *(workspace file from MES)*
  - "Scrap < 1.8%" *(same file)*
  - "Zero open 8Ds > 15 working days" *(workspace file from CAQ)*
  - "All 4 Azubis in 2. Lehrjahr rotate through Zelle 1 by Sep"
- **Day-to-day:** at the whiteboard by 07:30, walks 3 shifts over a week, sees every KPI on shopfloor displays.

#### Markus Schneider — Fertigungsleiter (L2, Prokurist, 18 yrs)
- **Responsibilities:** All 4 cells + planning + maintenance. Weekly GF review. Capex. Capacity interface to Vertrieb.
- **Goals:**
  - "Plant OEE ≥ 80%" *(aggregated)*
  - "Adherence to schedule ≥ 95%"
  - "Unplanned downtime < 3%"
  - "EV cell ramp: 40k units/month by Dec"
  - "Apprenticeship: 12 new Azubis start September"
- **Cascade:** his plant-OEE goal is the union of each Meister's cell-OEE — exactly where Vynaris's cascade proposal helps.

#### Dr. Jens Albers — Leiter F&E (L2, Prokurist, 15 yrs)
- **Responsibilities:** 55-person engineering. 3 platforms (valve, steering, EV). Roadmap, RFQs, prototype stages (A-/B-/C-/D-Muster).
- **Goals:**
  - "B-Muster EV-Valve ready for Bosch validation by Jun 30" *(milestone KR)*
  - "Zero major findings in Bosch technical audit 2026"
  - "R&D spend/revenue ≥ 4.5%"
  - "2 new patent filings"

#### Sabine Richter — Geschäftsführerin (L0, family, 8 yrs in role)
- **Responsibilities:** Firm strategy. Banks. Audit. Family dynamics.
- **Goals:**
  - "EBITDA margin ≥ 9%"
  - "Top-3 customer concentration < 60%" *(Bosch is currently 38%)*
  - "Close Porsche EV contract by year-end" *(binary)*
  - "Succession plan for 3 key Meister roles drafted"

### How they work today
- SAP / proAlpha ERP + MES on the shop floor.
- Shift handover notebooks. Morning Shopfloor-Meeting at 08:00 with line leads + production manager + QM — classic daily-standup, whiteboard of OEE, scrap, open 8Ds.
- QM runs FMEA / CP / control plans in heavy Excel or dedicated tools (Babtec, CAQ).
- Outlook is dominant. Teams uptake is slower than expected (GDPR + Betriebsrat concerns).
- KPIs posted on screens on the shop floor. Very visual.

### Vynaris implications from Schäfer Präzision
- **Works Council is lethal if framed wrong.** Agent must be **bonded to the person** (helps *them*, not the boss). Activity log is the person's, not management's. Crispness of this framing decides German enterprise deals.
- **Shift-based workers (L4–L6 production)** don't open laptops at 06:00. They interact with Vynaris via a shopfloor tablet or their Meister's laptop during the 08:00 SFM. We need a **shift-handover view** and a **shopfloor TV mode** (big numbers for one cell, auto-refresh).
- **Dual ladders:** can't assume a single hierarchy. Meister (L3 production) doesn't report to an Abteilungsleiter (L2 office) — both report to Fertigungsleiter but live in different cultures.
- **Apprentices (Azubis):** rotate through functions every 3–6 months — their manager changes. Flag with a "learner" attribute; skip "own goals" expectation.
- **German UI** is table stakes. i18n is Phase 4 minimum for this persona.
- **Data residency:** must run on EU infra. Self-hosted single-tenant is a huge sell.
- **Documentation rigor:** check-ins + activity logs have real compliance value (ISO / IATF audit trail). Lean into it.

---

## Persona 3 — Barrett & Lang LLP

**Midtown NYC · ~580 total · 380 attorneys + 200 business professionals · mid-BigLaw**

### Cultural context: attorney ladder + business-professional ladder

Two parallel tracks. Class year is everything for associates. The 6th-year bills at $1,100/hr, the 2nd-year at $650/hr; they get paid differently; they own different parts of a matter. Class year is the rotation axis for BigLaw.

```
LEGAL TRACK                            BUSINESS PROFESSIONAL TRACK
─────────────                          ──────────────────────────
Firm Chair / Managing Partner           Executive Director / COO
 │                                       │
Executive Committee                     Chief Officers (CFO, CMO, CIO, CHRO)
 │                                       │
Practice Group Leader                   Director (BD, KM, Pricing, ProfDev, ...)
 │                                       │
Sr. Equity Partner                      Sr. Manager
 │                                       │
Equity Partner                          Manager
 │                                       │
Non-Equity / Income Partner             Specialist / Sr. Analyst
 │                                       │
Senior Counsel / Of Counsel             Analyst / Coordinator
 │                                       │
Senior Associate (Yr 6–8)               Assistant / Secretary
 │
Mid-level Associate (Yr 3–5)
 │
Junior Associate (Yr 1–2)
 │
Summer Associate (10-wk intern)
```

**Non-equity partner:** ~51% of all BigLaw partners now. Title + salaried comp, no profit share. A holding pattern for strong-but-not-equity attorneys.

### Headcount by level (~580 total)

| Level | Attorney | Business | Approx. count |
|---|---|---|---|
| **L0 — Firm leadership** | Firm Chair, Deputy Chair, Exec Committee | Executive Director, CFO, CMO, CIO, CHRO | ~13 |
| **L1 — PG leaders / Chief officers** | 7–10 Practice Group Leaders | Directors (BD, KM, Pricing, ProfDev, Recruiting, Diversity Officer) | ~18 |
| **L2 — Senior partners** | Senior Equity Partners | Sr. Managers (BD Sr. Mgr per PG, Accounting Mgr, Conflicts Mgr) | ~30 |
| **L3 — Equity partners** | Equity Partners | Managers | ~95 |
| **L4 — Non-equity partners** | Income / Non-Equity Partners | Senior Analysts / Specialists (Pricing, KM Attorney, BD Specialist) | ~85 |
| **L5 — Of Counsel / Sr. Counsel** | Specialists, ex-partners, part-time | Analysts / Coordinators | ~65 |
| **L6 — Senior Associates** | Class Yr 6–8 *(up-or-out territory)* | — | ~70 |
| **L7 — Mid-level Associates** | Class Yr 3–5 | — | ~85 |
| **L8 — Junior Associates** | Class Yr 1–2 | — | ~70 |
| **L9 — Staff / Contract Attorneys** | — | — | ~15 |
| **L-Para — Paralegals** | Sr / Mid / Jr Paralegals | — | ~50 |
| **L-Admin — Support** | — | Legal Secretaries, Executive Assistants, Office Services, Facilities | ~80 |

Of 580: ~380 attorneys across 9 levels, ~200 business professionals.

### Departments

**Revenue generators (practice groups):**
1. M&A / Corporate
2. Litigation (commercial + securities)
3. Intellectual Property (patent prosecution + IP litigation)
4. Real Estate
5. Employment & Labor
6. Tax
7. Restructuring / Bankruptcy

**Revenue enablers (business professionals):**
8. Office of Managing Partner / Firm Chair
9. Finance & Accounting (WIP, AR, billing)
10. Business Development & Marketing (per-PG BD team + firm marketing)
11. Knowledge Management (precedent libraries, KM lawyers, AI initiatives)
12. Professional Development / Training
13. Recruiting (summer associates, lateral partners — its own function)
14. HR / People
15. IT & Cybersecurity
16. Conflicts / New Business Intake
17. Library / Research

### M&A Practice Group — deep view (~55 attorneys)

```
Practice Group Leader - M&A (L1, Senior Equity Partner, 22 yrs)
 │
 ├─ Senior Equity Partners (L2) — 5 people
 │    │ own biggest clients (PE funds, repeat strategics)
 │
 ├─ Equity Partners (L3) — 12 people
 │    │ originate, do substantive deal management
 │
 ├─ Non-Equity / Income Partners (L4) — 6 people
 │    │ service partner books, tested for equity
 │
 ├─ Of Counsel (L5) — 2 (specialists — tax-M&A, antitrust)
 │
 ├─ Senior Associates (L6) — 10 (Yr 6–8)
 │
 ├─ Mid-level Associates (L7) — 12 (Yr 3–5)
 │
 ├─ Junior Associates (L8) — 8 (Yr 1–2)
 │
 ├─ M&A Paralegal Manager (1)
 │
 └─ 2 PG-dedicated BD Managers (from Business track)
```

**Matrix reality:** A deal team forms across class years — 1 Senior Partner + 1 Equity Partner + 1 Senior Associate + 2 Mid-levels + 1 Junior + 1 Paralegal. An associate has 3–5 deals running simultaneously, each led by a different partner. One associate, 3–5 managers at once. **The single reporting tree is nearly fictional.** The real working unit is the **matter team** — spins up, runs 3–9 months, spins down.

### Business professional deep view — Finance (~20 people)

```
CFO (L0)
 │
 ├─ Director of Finance (L1)
 │   │
 │   ├─ Accounting Manager (L3)
 │   │   ├─ Sr. Accountant (L4)
 │   │   ├─ Accountant (L5)
 │   │   └─ AP Clerk, AR Clerk
 │   │
 │   └─ Billing Manager (L3)
 │       ├─ Sr. Billing Analyst (L4) — 3
 │       └─ Billing Coordinator (L5) — 4
 │
 ├─ Director of Pricing (L1) — newer strategic role
 │   ├─ Pricing Manager (L3)
 │   └─ Pricing Analyst (L4) — 2
 │
 └─ Controller (L2)
     ├─ Sr. Financial Analyst (L4)
     └─ Financial Analyst (L5)
```

### Representative people & goals

#### Jamie Chen — Junior Associate Yr 1, M&A (L8, 4 months out of law school)
- **Responsibilities:** Due diligence review, first drafts of reps & warranties, research memos, running the virtual data room.
- **Reality:** Works until 2am during deal crunches. Has 4 partners "supervising" her across 3 active deals.
- **Goals:**
  - "1,900 billable hours" *(private — manager-chain only)*
  - "Daily time entry by 10pm next day" *(workspace file)*
  - "All assigned CLEs completed by Dec 31"
  - "Evaluation rating ≥ 'strong' on each deal I worked on"
- **What she needs from Vynaris:** help drafting contemporaneous time entries ("what did I do Monday 9am–11am on the Acme deal?"), deadline reminders across 3–5 concurrent deals, KM lookup ("find last 10 reps-and-warranties we wrote for PE buyers in healthcare").

#### Michael Ross — Mid-Level Associate Yr 4, M&A (L7)
- **Responsibilities:** Runs workstreams, supervises juniors, first calls with clients on routine matters, owns sections of agreements.
- **Goals:**
  - "2,000 billable hours" *(private)*
  - "Lead 2 deals as day-to-day associate from signing to closing" *(binary milestones)*
  - "Evaluation ≥ 'outstanding' from 2+ partners"
  - "Publish 1 client alert / thought-leadership piece"

#### Sarah Kim — Equity Partner, M&A (L3, 11 yrs, 2 yrs since partnership)
- **Responsibilities:** 3–4 client relationships. 12–18 deals/year. Mentors 3 associates.
- **Goals:**
  - "Originations ≥ $3.5M" *(private; manager-chain + firm-chair visible)*
  - "Billable hours ≥ 1,800"
  - "Write-downs < 6% of my WIP"
  - "Close 1 new client relationship this year"

#### David Wright — Practice Group Leader, M&A (L1, 22 yrs)
- **Responsibilities:** Group strategy, hiring, conflict management between partners, budget, lateral recruiting.
- **Goals:**
  - "M&A group revenue ≥ $125M"
  - "Group realization ≥ 88%" *(URL → Elite)*
  - "Win 3 of 5 key RFPs this year"
  - "Recruit 2 lateral partners for the healthcare-M&A gap" *(binary)*
  - "Chambers ranking: maintain Band 2"

#### Nisha Patel — BD Manager, M&A Practice Group (L3, 7 yrs, non-lawyer)
- **Responsibilities:** Embedded BD — pitches, Chambers submissions, client alerts, event coverage. Reports into BD org, sits with M&A.
- **Goals:**
  - "50 pitch documents produced, 10+ new-client wins attributed"
  - "8 Chambers submissions on time by Feb 28"
  - "2 firm-hosted M&A client events with ≥ 50 attendees each"
  - "M&A client alert cadence: 2/month, open-rate ≥ 22%"

#### Leah Goldstein — CFO (L0, 9 yrs)
- **Responsibilities:** Firm P&L, bank relationships, cap calls, partner compensation modeling.
- **Goals:**
  - "PPP ≥ $2.1M"
  - "DSO < 75 days"
  - "WIP > 120 days reduced 30%"
  - "Close Q in 5 working days"

#### Priya Shah — Senior Paralegal, Litigation (L-Para, 14 yrs, runs internal lit-support team)
- **Responsibilities:** E-discovery coordination, deposition support, court filings for Lit partners.
- **Goals:**
  - "Billable hours ≥ 1,600"
  - "Zero missed court filing deadlines" *(binary — any miss is a fire)*
  - "E-discovery TAR accuracy > 92% on 4 matters this year"

### The matter (deal) primitive

A law firm thinks in **matters**, not goals. Every piece of work has a matter number. Time, conflicts, AR all run against matter numbers. Partners' goals ("$3.5M originations") roll up from the matters they originated.

For Vynaris:
- Matters ≈ channels with extra structure: matter number, client, responsible partner, billing attorney, team members, open/closed state.
- A partner's originations goal pulls from matters they originated ("sum WIP + collected from my originated matters YTD").

### How they work today
- Elite / Aderant for time + billing.
- iManage / NetDocuments for documents (everything is a document).
- Litify / Salesforce / Foundation as firm CRM + BD tracking.
- Chambers / Legal 500 rankings dominate BD conversations.
- Outlook is sacred. Teams tolerated. Slack rare (security).
- Daily time entry → "contemporaneous" billing is a religion.
- Weekly partner meetings; monthly all-partners; annual partner off-site.

### Vynaris implications from Barrett & Lang
- **Multi-manager / matrix is mandatory.** One associate has 3–5 partners supervising them concurrently. `manager_id` alone is insufficient. Need a `TeamMembership(person_id, team_id, role_in_team)` model.
- **Class year as a first-class attribute** on attorneys — feeds expected billable hours, realization, bonus grid.
- **Private goals with strict scope:** billable-hour goals, origination goals, evaluation ratings cannot be org-visible. We need a `private: [list_of_person_ids]` visibility option, not just team/org/private.
- **Matter / project as sibling to Goal:** matters host most discussion. Goals are performance framing. Both need sidebar presence (separate sections).
- **Conflicts / ethical-wall enforcement:** some people *cannot* see certain matters (acquirer vs target representation). Conflicts need to gate channel access, not just filter visibility.
- **Time-entry drafting** is the highest-leverage agent capability for lawyers. Feed calendar + doc edit history + conversation snippets → draft contemporaneous narrative. Ship as a dedicated skill.
- **Self-hosted + zero outbound** = attorney-client privilege story. Claude subscription-auth + local deployment lands the pitch.
- **Billable-hour math as pitch:** 30-min saved per associate per day at $650/hr = ~$2.2M/year for a 30-associate practice group. That's the lead line for BigLaw.

---

## Persona 4 — Nimbus Analytics

**NYC + remote-US · ~200 people · Series C · $35M ARR · cloud data platform for enterprise**

Sells a data platform to mid-market and enterprise companies. Competes with Snowflake at the low end, legacy data stacks in the upper mid-market. GTM-heavy org — revenue team is ~30% of headcount, and the entire company's pulse is quarterly ARR attainment.

### Cultural context: segmented GTM + quota as religion

B2B SaaS at Series C runs on **segmentation + quota**. Customer base is split into SMB / Mid-Market / Enterprise, each with its own rep profile, sales motion, deal size, and expected win rate. Quotas are declared quarterly. Commissions depend on them. Boards ask about them monthly. **This is the axis everything rotates around** — not class year (law), not OEE (mfg), not LC rate (trading).

### The ladders (three distinct GTM ladders + product tracks)

```
 SALES                      CUSTOMER SUCCESS         MARKETING
 ──────                     ─────────────────        ─────────
 CRO                        VP CS → CRO              CMO
  │                          │                        │
 SVP / CSO                  Director CS              VP Marketing
  │                          │                        │
 VP Sales (Enterprise /     Manager CS               Director (Demand Gen /
  Mid-Market)                │                         PMM / Content / Brand /
  │                         Principal CSM             Customer Mktg / Field)
 Director (segment /         │                        │
  region)                   Senior CSM               Senior Marketing Manager
  │                          │                        │
 Manager (5-10 reps)        CSM                      Marketing Manager
  │                          │                        │
 Strategic AE (Enterprise)  Associate CSM            Marketing Specialist
  │                          │                        │
 Enterprise AE              CS Ops                   Marketing Coordinator
  │
 Mid-Market AE              [parallel: Renewals Mgr]
  │
 SMB / Inside AE
  │
 SDR / BDR
```

Separately: **Engineering** (CTO → VPs → Directors → Eng Mgrs → Staff/Senior/Mid/Jr Eng · ~60 people), **Product** (CPO → VP/Dir → GPM → PM → APM · ~12), **Design** (~8), **RevOps** (cross-cutting, reports to CRO or CFO · ~5), **G&A** (Finance, People, Legal, IT · ~25).

**Industry ratios that shape org design:**
- **SDR : AE ≈ 1 : 2.6** (each SDR supports ~2–3 AEs)
- **Sales manager : reps ≈ 1 : 5–10**
- **Pipeline coverage:** 3–5× quota for Enterprise, 3–4× for Mid-Market, 4–6× for SMB
- **Pipeline sourcing mix:** ~25–30% marketing, ~40% SDRs, ~30% AE self-sourcing
- **CSM coverage:** 5–20 high-touch / 20–60 mid-touch / 100–250 tech-touch accounts per CSM
- **Median enterprise AE quota ~$800K ACV**, ~58% of reps hit quota in 2025
- **CSM NRR target 110–120%** at growth stage

### Headcount by function (~200)

| Function | Headcount | Breakdown |
|---|---|---|
| **Engineering** | ~60 (30%) | CTO + 2 VPs + 4 Directors + 12 EMs + ~40 ICs across platform / product / data eng / SRE |
| **Product** | ~12 (6%) | CPO + 2 Dir + 9 PMs |
| **Design** | ~8 (4%) | VP Design + Manager + 6 ICs |
| **Sales** | ~35 (18%) | CRO + 2 VPs (Enterprise / MM) + 4 Directors + 5 Managers + 8 Strategic/Ent AEs + 10 MM AEs + 4 SMB AEs + 6 SDRs + 2 SEs |
| **Customer Success** | ~20 (10%) | VP CS + 2 Directors + 3 Managers + 2 Principal CSMs + 8 Sr/mid CSMs + 5 Associate CSMs |
| **RevOps** | ~5 (2.5%) | Director + 4 analysts / systems |
| **Marketing** | ~25 (12.5%) | CMO + 6 Directors (DG, PMM, Content, Brand, Customer Mktg, Field) + ~12 Managers/Sr specialists + 6 Specialists/Coordinators |
| **G&A** | ~25 (12.5%) | CFO + CHRO + COO + ~22 across Finance, People, Legal, IT, Facilities |
| **Executive** | ~8 (4%) | CEO + 7 C-suite |

### Sales deep tree (~35 people)

```
CRO (L0)
 │
 ├─ VP Sales, Enterprise (L1) — 6 direct reports
 │   ├─ Director, Enterprise East (L2)
 │   │   ├─ Manager, Enterprise (L3)
 │   │   │   ├─ Strategic AE (L4) — 3 ($1.2M quota each)
 │   │   │   └─ Sales Engineer (L4) — 1
 │   ├─ Director, Enterprise West (L2) (mirror)
 │   │   └─ Strategic AE (L4) — 2
 │   └─ Strategic AE, National accounts (L4) — 2 (report directly to VP)
 │
 ├─ VP Sales, Mid-Market (L1)
 │   ├─ Director, MM East (L2)
 │   │   ├─ Manager, MM (L3)
 │   │   │   └─ MM AE (L4) — 5 ($650K quota each)
 │   └─ Director, MM West (L2) (mirror)
 │
 ├─ Head of SDR / Pipeline (L2)
 │   ├─ Manager, SDR (L3)
 │   │   ├─ Team Lead SDR (L4) — 1
 │   │   └─ SDR (L5) — 5 (20 SQLs/mo quota each)
 │
 └─ Head of RevOps (L1, dotted line to CFO)
     ├─ Manager, RevOps (L3)
     ├─ Sr. Sales Analyst (L4) — 2
     └─ CRM/Systems Admin (L4) — 1
```

### Marketing deep tree (~25 people)

```
CMO (L0)
 │
 ├─ VP Marketing / Head of Growth (L1)
 │   │
 │   ├─ Director, Demand Gen (L2)
 │   │   ├─ Sr. Paid Marketing Manager (L3) — 1
 │   │   ├─ ABM Manager (L3) — 1
 │   │   └─ Marketing Automation Manager (L4) — 1
 │   │
 │   ├─ Director, Product Marketing (L2)
 │   │   ├─ Sr. PMM (L4) — 2 (one per product line)
 │   │   └─ Competitive Intel Analyst (L4)
 │   │
 │   ├─ Director, Content & SEO (L2)
 │   │   ├─ Content Manager (L4) — 2 (writers)
 │   │   └─ SEO Specialist (L4)
 │   │
 │   ├─ Director, Brand (L2)
 │   │   ├─ Brand Manager (L4)
 │   │   └─ Designer (L5) — 2
 │   │
 │   ├─ Director, Customer Marketing (L2)
 │   │   └─ Customer Mktg Manager (L4)
 │   │
 │   └─ Director, Field & Events (L2)
 │       └─ Event Marketing Coordinator (L5)
 │
 └─ Marketing Ops Manager (L3, dotted line to RevOps)
```

### Customer Success deep tree (~20 people)

```
VP Customer Success (L1, reports to CRO)
 │
 ├─ Director, Enterprise CS (L2)
 │   ├─ Principal CSM (L3) — 2 (strategic largest accounts, $3M book each)
 │   └─ Sr. CSM (L4) — 4 (high-touch, 10-15 accounts each)
 │
 ├─ Director, MM CS (L2)
 │   ├─ Manager, MM CS (L3)
 │   │   ├─ Sr. CSM (L4) — 2
 │   │   └─ CSM (L5) — 4 (20-30 accounts each)
 │
 ├─ Manager, Pooled / Digital CS (L3)
 │   └─ Associate CSM (L5) — 4 (100-250 tech-touch accounts each)
 │
 ├─ CS Ops Analyst (L4) — 1
 │
 └─ Renewals Manager (L3) — 1 (dotted line to Sales)
```

### Representative people — goals at each level

#### Marcus Chen — SDR (L5, 8 months out of undergrad)
- **Responsibilities:** 60+ outbound touches/day (calls, emails, LI DMs). Qualify inbound leads. Book meetings for AEs in his territory.
- **Reality:** Salesforce, Outreach/Salesloft, Gong listens on first calls. Weekly 1:1 with SDR manager. Daily standup, Monday territory huddle.
- **Goals:**
  - "20 meetings booked / month (target), 30 = stretch"
  - "8 SQLs per month (meeting held + BANT-qualified)"
  - "Activity: 300 calls + 500 emails + 100 LI / week (consistency matters)"

#### Priya Shah — Mid-Market AE (L4, 3 yrs)
- **Responsibilities:** 25 target accounts, deals $40–150K ACV, partners with SE for demos.
- **Goals:**
  - "$650K ACV quota for FY" *(private; mgr + VP + CRO visible)*
  - "Pipeline 4× coverage at Q-start" *(URL from Salesforce)*
  - "Win rate SQL → Closed Won ≥ 35%"
  - "Average deal velocity ≤ 70 days from SQL → close"

#### Jake Park — Strategic AE, Enterprise (L4, 6 yrs)
- **Responsibilities:** 8–12 named accounts (Fortune 2000), multi-threaded deals $150K+, executive engagement.
- **Goals:**
  - "$1.2M ACV quota" *(private)*
  - "4 new logos / year" *(at least)*
  - "Pipeline 5× coverage"
  - "5 executive briefings per quarter"
  - "Win rate on committed pipeline ≥ 40%"

#### Nina Rodriguez — Senior CSM, Enterprise (L4, 4 yrs)
- **Responsibilities:** 12 high-touch enterprise accounts, $4M book. Runs QBRs, expansion plays, health scoring.
- **Goals:**
  - "NRR 115% across book"
  - "GRR ≥ 95% (< 5% logo churn)"
  - "Expansion pipeline = 2× book × segment-avg expansion rate"
  - "Time-to-first-value on new enterprise accounts ≤ 45 days"
  - "Champion-mapped on all accounts > $200K ARR"

#### David Kumar — Demand Gen Manager (L3, 5 yrs)
- **Responsibilities:** Owns paid media (Meta, Google, LinkedIn), ABM tools (6sense/Demandbase), nurture programs.
- **Goals:**
  - "Marketing-sourced pipeline $8M / quarter"
  - "CAC payback ≤ 18 months" *(company-wide KPI, his contribution)*
  - "MQL → SQL conversion ≥ 25%"
  - "Ship 1 major campaign per quarter with attribution report"

#### Rachel Soh — Senior Product Marketing Manager (L4, 6 yrs)
- **Responsibilities:** Positioning + launches for the AI-features product line. Sales enablement. Competitive.
- **Goals:**
  - "Ship 2 major launches this year with full enablement (deck, battlecards, demo script, pricing)"
  - "Competitive win-rate vs Snowflake ≥ 35%" *(tracked in Salesforce on closed-lost reason)*
  - "Sales-enablement NPS from AEs ≥ 8/10"

#### Elena Vasquez — VP Sales, Enterprise (L1, 12 yrs)
- **Responsibilities:** 8 Strategic AEs + 1 Director + 2 SEs + 1 business development partner.
- **Goals:**
  - "Enterprise segment $9M new ARR this FY"
  - "Enterprise rep attainment 70%+ (industry median 58%)"
  - "Hire 2 Strategic AEs in Q2"
  - "Close first healthcare-vertical Fortune 500 logo (strategic initiative)"
  - "Ramp time for new AEs ≤ 5 months to first deal"

#### Sarah Oberman — CRO (L0, 15 yrs)
- **Responsibilities:** All revenue functions — Sales + CS + RevOps. Board KPIs. Comp plans. Hiring.
- **Goals:**
  - "$50M ARR by FY end · net new ARR $15M"
  - "NRR 120%"
  - "GRR 92%"
  - "CAC payback ≤ 18 months"
  - "70% of quota-carrying reps at 80%+ attainment"
  - "Magic Number ≥ 0.8"

### How they work today
- **Salesforce** is the source of truth. Every opp, every activity, every forecast.
- **HubSpot / Marketo** for marketing. **Outreach / Salesloft** for sales outbound. **Gong / Chorus** for call intelligence.
- **Slack** is core comms (none of the Works-Council / attorney-privilege baggage).
- **Notion / Confluence** for docs. **Linear / Jira** for engineering + product.
- Weekly forecast call (Mon). Monthly business review. Quarterly kickoff. Pipeline council / deal desk for deals > $100K.
- Ramp / Carta / Gusto / Rippling for ops.

### Vynaris implications from Nimbus
- **Quota + pipeline as first-class KR sources** — both pulled from Salesforce via URL on a daily cadence. Agent can detect drift (pipeline coverage slipping, stalled opps) before forecast call.
- **Segmented teams with their own cascade trees** — Enterprise / MM / SMB are effectively three mini-orgs. A VP-level goal cascades differently per segment. Need multi-tree cascade (not just one tree).
- **Account-based channels** (ABM) — `#acct-johnson-and-co` for a target enterprise account, spun up when it enters pipeline, spun down when closed. Short-lived but critical primitive.
- **Commission-linked goals** — when a goal affects comp, visibility + audit tighten. Mgr-chain + CRO + CFO + HR payroll. Goal lineage must be tamper-evident.
- **Private-to-viewer-chain** — same need as law: rep-level quota goals cannot be team-visible.
- **Pod model (AE + SE + SDR + CSM)** — a matrix team formed per segment + geography. Same person is in multiple pods. Team-membership model is mandatory, not nice-to-have.
- **Attribution transparency** — when marketing claims pipeline sourced + SDR claims same + AE self-sourced — who owns attribution? Agent should surface the conflict, not paper over it.
- **Gong call summaries** as agent context — the agent drafting a check-in for an AE should ingest the last week's call transcripts to understand deal state.

---

## Persona 5 — Luma

**Los Angeles · ~120 people · $45M revenue · 4 yrs old · DTC skincare · Shopify + Sephora wholesale + 2 owned retail stores**

Consumer brand. Performance-marketing driven growth. Marketing is 35–40% of headcount. Creative is the second-largest function. Engineering is nearly nonexistent (outsourced or Shopify-native). Product is *formulation*, not software.

### Cultural context: creative rhythm + performance reality

B2C DTC brands are **bifurcated cultures** — half the org thinks in *brand / narrative / creative*, half thinks in *ROAS / CAC / efficiency*. The CMO's hardest job is keeping both sides aligned. **Weekly creative reviews** (Wed) + **weekly perf standups** (Tue) + **monthly business review** = the rhythm.

Seasonality drives everything. Q4 (BFCM) is 35–45% of the year. New Year and Mother's Day are events. The rest of the year is slower tempo — except launches.

**Industry benchmarks that shape org design:**
- Marketing team composition at mature DTC: **38–42% perf marketing + lifecycle**, **18–22% creative**, **12% mktg ops**, rest split brand/content/influencer.
- Typical ROAS benchmarks: blended 2.0–3.0 · Meta cold 2.2 · retargeting 5–10 · Google Shopping 4+.
- Email = ~27% of total revenue on average (Klaviyo benchmark). A healthy flow share = 40%+.
- LTV:CAC target 3:1+ (below 2:1 = unit economics dying).
- Subscription churn target ≤ 4% monthly for healthy retention.

### The ladders

```
 MARKETING (+ CREATIVE)       E-COM / OPS              SUPPLY / PRODUCT
 ──────────────              ─────────────            ─────────────────
 CMO                         VP Digital / COO         VP Operations
  │                           │                        │
 VP Growth · VP Brand         Director                Director (PD / SC / Logistics)
  │                           │                        │
 Director (per channel:       Manager                 Manager (PD / QC / Planning)
  DG · Lifecycle · Brand ·    │                        │
  Creative · Influencer ·    Senior Specialist        Sr. Chemist / Buyer / Planner
  Content · Ops)              │                        │
  │                          Specialist               Coordinator / Analyst
 Sr. Manager / Manager        │
  │                          Coordinator
 Sr. Specialist / Manager
  │
 Specialist
  │
 Coordinator / Intern
```

Retail has its own short ladder: Retail Associate → Store Manager → District/Area Manager → Director of Retail.
Wholesale (Sephora, etc.) has: Wholesale Account Manager → Director of Wholesale.

### Headcount by function (~120)

| Function | Headcount | Breakdown |
|---|---|---|
| **Marketing (+ Creative)** | ~47 (39%) | CMO + 2 VPs (Growth / Brand) + 8 Directors + 18 Managers/Sr specialists + 18 Specialists/Coordinators (includes 15 in Creative studio) |
| **E-commerce / Digital** | ~8 (7%) | Head of E-com + 4 Managers + 3 specialists (CRO, subscription, web-dev) |
| **Product Development (formulation)** | ~10 (8%) | Director + 3 Sr. Chemists + 3 Chemists + 1 Packaging Designer + 1 Regulatory Manager + 1 Coordinator |
| **Supply / Ops / Logistics** | ~15 (13%) | COO + Director SC + Manager Procurement + Manager Planning + Manager 3PL + Buyers + Analysts + Coordinators |
| **Retail / Wholesale** | ~12 (10%) | Director Retail + Director Wholesale + 2 Wholesale AMs + 6 Retail Associates (2 stores × 3 per store) + 2 Store Managers |
| **Customer Experience (CX)** | ~12 (10%) | Head of CX + 2 Managers + 8 Specialists + 1 Community Mod |
| **Finance / People / Legal / IT** | ~12 (10%) | CFO + CHRO + Legal Counsel + ~9 ICs |
| **Executive** | ~4 (3%) | CEO / Founder + CMO + COO + CFO |

### Marketing + Creative deep tree (~47 people)

```
CMO (L0)
 │
 ├─ VP Growth / Performance (L1)
 │   ├─ Director, Paid Media (L2)
 │   │   ├─ Sr. Performance Manager, Meta (L3)
 │   │   ├─ Sr. Performance Manager, Google/TikTok (L3)
 │   │   └─ Performance Specialist (L4) — 2
 │   ├─ Director, Lifecycle & CRM (L2)
 │   │   ├─ Email Lifecycle Manager (L3)
 │   │   ├─ SMS Manager (L3)
 │   │   └─ CRM / Loyalty Specialist (L4)
 │   └─ Marketing Analytics Manager (L3)
 │
 ├─ VP Brand & Creative (L1)
 │   ├─ Director, Creative Studio (L2)
 │   │   ├─ Associate Creative Director, Digital (L3)
 │   │   │   ├─ Sr. Designer (L4) — 2
 │   │   │   ├─ Designer (L5) — 3
 │   │   │   ├─ Motion Designer (L5) — 2
 │   │   │   └─ Sr. Copywriter (L4)
 │   │   ├─ Associate Creative Director, Print / OOH (L3)
 │   │   │   └─ Designer (L5)
 │   │   ├─ Art Director / Photographer (L4)
 │   │   └─ Production Coordinator (L5)
 │   ├─ Brand Manager (L3)
 │   ├─ Social & Community Manager (L3)
 │   │   └─ Social Coordinator (L5)
 │   └─ PR Lead (L4)
 │
 ├─ Director, Influencer & Partnerships (L2)
 │   ├─ Sr. Influencer Manager (L3)
 │   └─ Affiliate Coordinator (L5)
 │
 ├─ Director, Content & Organic (L2)
 │   ├─ Content Manager (L3)
 │   └─ SEO Specialist (L4)
 │
 └─ Marketing Ops Manager (L3)
     └─ Analytics Coordinator (L5)
```

### Representative people — goals at each level

#### Maya Tran — Performance Marketing Specialist, Meta (L4, 2 yrs)
- **Responsibilities:** Daily ad-set optimization in Meta Ads Manager. Manages $300K/mo ad budget. Creative testing sprint (3–5/week).
- **Goals:**
  - "Meta blended ROAS ≥ 2.4 (monthly)" *(workspace file from Motion / Triple Whale export)*
  - "CAC on new customers ≤ $42"
  - "Scale spend to $350K/mo while holding efficiency"
  - "Ship 12 creative tests per month, retain top 3 winners"

#### Jordan Ellis — Email Lifecycle Manager (L3, 5 yrs)
- **Responsibilities:** All email + SMS flows (Klaviyo + Attentive). Campaign calendar. Segmentation.
- **Goals:**
  - "Email = 26% of total revenue" *(URL from Klaviyo)*
  - "Flow revenue share ≥ 40%" *(welcome · browse-abandon · cart-abandon · post-purchase · win-back)*
  - "Open rate ≥ 38% on campaigns"
  - "Subscription churn ≤ 4.5% monthly" *(Recharge dashboard URL)*
  - "Launch 2 new triggered flows this quarter"

#### Riley Park — Senior Copywriter (L4, 4 yrs)
- **Responsibilities:** Tier-1 campaign copy, product launch narrative, major email + site copy.
- **Goals:**
  - "Deliver 4 tier-1 campaigns on time this quarter" *(binary milestones)*
  - "Maintain brand-voice consistency ≥ 90% on quarterly audit" *(manual audit score)*
  - "Lead 1 major brand editorial / manifesto piece"

#### Sam Cohen — Director, Paid Media (L2, 8 yrs)
- **Responsibilities:** Entire performance function across Meta/Google/TikTok. $1.4M monthly budget.
- **Goals:**
  - "Blended paid ROAS ≥ 2.1"
  - "Overall paid-sourced CAC ≤ $48"
  - "Channel mix — Meta 55% / Google 25% / TikTok 15% / other 5%"
  - "Contribution margin after paid spend ≥ 35%"
  - "Weekly channel-health report to leadership"

#### Nina Patel — Director, Influencer Partnerships (L2, 6 yrs)
- **Responsibilities:** Creator + affiliate programs. Seeding. UGC generation. Whitelisting.
- **Goals:**
  - "40 paid partnerships / month (creators + micro-influencers)"
  - "Attributed revenue $180K / month" *(URL from Attentive + promo-code breakdown)*
  - "Average UGC CPM $22 (vs $45 studio-produced)"
  - "2 long-term whitelist partnerships per quarter"

#### Alex Ramirez — Brand Manager (L3, 4 yrs)
- **Responsibilities:** Brand positioning. Guidelines. Launch strategy. Brand health tracking.
- **Goals:**
  - "Aided brand awareness +6pp in 18–34 F demo" *(quarterly survey, manual)*
  - "Brand-search volume +35% YoY" *(URL from Google Search Console)*
  - "Launch Serum-Plus line — brand plan, creative direction, comms strategy shipped by Jun 1" *(binary)*
  - "Quarterly brand health tracker published"

#### Dr. Emma Chen — Director, Product Development (L2, 10 yrs, PhD chemistry)
- **Responsibilities:** Formulation R&D + regulatory + packaging. Pipeline of new SKUs 12–18 months out.
- **Goals:**
  - "Ship 6 new SKUs this year on roadmap" *(milestone per SKU)*
  - "Pipeline 18 SKUs in formulation (12+ mo out)"
  - "Zero regulatory findings on any launch" *(binary audit)*
  - "Cost-per-unit reduction ≥ 8% on 3 existing SKUs" *(margin play)*

#### Lisa Moreno — Head of E-commerce (L1, 7 yrs)
- **Responsibilities:** Site experience, CRO, subscription program.
- **Goals:**
  - "Site conversion 2.9% (vs benchmark 2.4%)"
  - "AOV $62 (baseline $54)"
  - "Subscription active users 15,000"
  - "Subscription churn ≤ 4% monthly"
  - "Checkout drop-off ≤ 22%"

#### Sofia Torres — Director, Wholesale (L2, 5 yrs)
- **Responsibilities:** Sephora + 3 regional retailers. Trade marketing. Store sell-through.
- **Goals:**
  - "Sephora wholesale revenue $8M"
  - "Sephora sell-through ≥ 35 units/week on top-3 SKUs at top-50 stores"
  - "Sign 2 new retail partners this year" *(binary)*
  - "Trade-marketing ROI 2.5×"

#### Chris Park — Head of CX (L2, 4 yrs)
- **Responsibilities:** 8-person support team on Gorgias (email + chat + Instagram DMs).
- **Goals:**
  - "First-response time ≤ 4 hours" *(Gorgias URL, down from 5.5)*
  - "CSAT ≥ 4.7 / 5"
  - "First-contact resolution ≥ 78%"
  - "Self-service deflection ≥ 32%" *(Shopify help-center analytics)*

#### Priya Mahajan — CMO (L0, 9 yrs)
- **Responsibilities:** Marketing + Creative + Brand + E-com.
- **Goals:**
  - "FY revenue $60M"
  - "Blended CAC $38 (down from $45)"
  - "LTV:CAC 3.2:1 (up from 2.9:1)"
  - "Aided brand awareness hits 28% in target demo"
  - "Ship Serum-Plus line launch with $4M first-90-day revenue"

### How they work today
- **Stack:** Shopify (site) · Klaviyo (email) · Attentive (SMS) · Gorgias (CX) · Recharge (subscriptions) · NetSuite (ops + finance) · Meta / Google / TikTok Ads · Triple Whale / Northbeam (attribution) · Motion (creative swapping) · Asana (campaign ops) · Slack (comms).
- **Rhythm:** Tuesday perf-marketing standup, Wednesday creative review, Thursday lifecycle/email review, monthly business review. Quarterly brand-health tracker. Always-on campaign calendar.
- **Seasonal compression:** Q4 (BFCM + holiday) is its own project. Launch mode for each new SKU is its own project.

### Vynaris implications from Luma
- **Campaign as a first-class primitive** — separate from Goal. A campaign has: brief, creative assets, budget, start/end, target KPI, channel, owning PM/creative. Campaign owns its own channel. A CMO's goal references campaigns; a performance manager's goal is assigned per-campaign.
- **Channel-level KR sources** — ROAS per ad channel updates daily via URL poll (Triple Whale, Northbeam, Meta Ads, Google Ads). This is *the* DTC data-source pattern.
- **External collaborators** — creators, influencers, freelance designers, agencies are *not* employees but appear in channels and in goal attribution. Need an "external" person-type that can be invited, sees scoped channels, doesn't count toward headcount.
- **Creative review workflow** — weekly rhythm of brief → design → review → approve → ship. Channel for creative reviews, artifacts = creative files, threading on each round of feedback.
- **Attribution source transparency** — when Triple Whale says $X and Meta says $Y and Shopify says $Z, agent should surface the gap rather than pick one. Multi-source KRs need reconciliation UI.
- **Peak season mode** — BFCM, product launches, Mother's Day etc. are high-intensity windows. Goals get more aggressive, cadence switches to daily, some "normal-season" goals get paused. Need a mode-switch primitive tied to a date range.
- **Brief-to-post workflow** — from creative brief → copy draft → design → motion → paid placement. Agent could automate the hand-off coordination.
- **Margin as a computed KR** — (revenue − COGS − shipping − paid − fulfillment) / revenue — can be derived from multiple sources. This is an example of a *formula-backed* KR, not a single-source pull.

---

## Cross-persona design implications

These aren't features — they're primitives the product is missing or must honor.

### 1. Level as a first-class field on Person
Currently: name, title, email, manager_id.
Needed: `level` (integer 0–9) + `level_label` (e.g. `"L3 · Meister"`, `"AM"`, `"Yr 4 Associate"`).
Goal dashboards group by level. Cascade respects levels. Bonus bands and rating norms plug in later.

### 2. Multi-manager / team-membership model
`Person.manager_id` is insufficient for law firms and any matrix org.
Needed: `TeamMembership(person_id, team_id, role_in_team, is_lead)`. Teams can be practice groups, cells, desks, or matter teams. Goals visible to reporting-tree ∪ team-memberships.

### 3. Matter / project primitive
Separate from Goal and Channel. A Matter has: matter number, client, responsible lead, billing owner, team, open/closed state. Matters have their own channel (or ARE a channel with extra metadata). Goals can reference Matters. Critical for law; useful for manufacturing (platforms / SOP projects); less so for trading.

### 4. Private-to-specific-people visibility
Current: `private` / `team` / `org`.
Needed: `private + explicit_viewer_ids`. Billable-hour goals must be visible to the associate + manager chain + firm chair + CFO — not the whole firm.

### 5. Watcher without ownership
A Vorarbeiter doesn't own goals but follows his Meister's cell OEE. A Junior Associate follows deal-team matters. Currently `GoalWatcher` exists in the model; surface it in UI and make it a real primitive for the non-owning workforce.

### 6. Cascade proposals at goal creation
When an L2–L3 creates a goal, UI asks: "Also create matching sub-goals for your N direct reports?" (default on when manager has reports). Reflects how Indian deep-hierarchy orgs work and how Fertigungsleiter → Meister rollups work.

### 7. Shift / part-time / learner person modes
`Person.working_mode`: `full-time` | `shift` | `apprentice` | `part-time` | `contractor`.
Shift workers default to *no goals owned + watcher on team goals*.
Apprentices (Azubis, summer associates) don't own goals — they rotate. Skip the expectation.

### 8. Demo org pack (first-boot choice)
On first boot, user can pick:
- **"Indian trading house (180)"** — Sanghavi
- **"German Mittelstand (650)"** — Schäfer
- **"NYC law firm (580)"** — Barrett & Lang

Each seeds 12–18 representative people across realistic levels, 6–10 goals with realistic KRs, 3–5 matter/channel equivalents. First-time evaluators don't stare at a blank page.

### 9. Data source patterns required (by frequency across personas)

| Source | Frequency | Example |
|---|---|---|
| **Workspace file (CSV/Excel)** | Dominant — every org has a weekly "export from X, drop here" rhythm | OEE dump from MES, LC register from bank, WIP from Elite |
| **URL / polled endpoint** | ~30% of KRs when systems expose APIs | Bosch supplier portal, Elite API, Apollo/Lemlist metrics |
| **Manual** | Always needed — exec-level goals resist automation | PPP, customer concentration, strategic milestones |
| **Email / attachment ingest** | Phase 3 — common in QM (Bosch PPM reports via email), legal (court filings) | Per-customer PPM emails, opposing-counsel filings |
| **Script / agent-computed** | Phase 3 — agent runs a query, returns a number | "SQL across matters for partner origination" |

### 10. Rhythm primitives (check-in cadence)

| Archetype | Dominant rhythm | What check-in cadence looks like |
|---|---|---|
| **Sanghavi (trading)** | Weekly MIS, daily WhatsApp | Weekly check-ins + event-based (shipment, LC event) |
| **Schäfer (manufacturing)** | Daily 08:00 SFM | Daily check-ins on cell-level goals; weekly at plant/department level |
| **Barrett (law)** | Contemporaneous time entry + weekly partner meetings | Weekly check-ins on partnership goals; matter-level updates on every substantive event |

Default: weekly. Switchable to daily (manufacturing cells, active M&A deals) or monthly (R&D, strategic initiatives). Phase 2.

### 11. Confidentiality modes we don't yet support
- **Per-goal access list** (ethical wall).
- **Manager-chain-only** visibility that blocks even firm-wide admin from seeing content (privilege concerns).
- **Audit log of who viewed** a goal channel (ISO / SOC 2 / attorney-regulator asks).

### 12. Agent participation by persona

| Persona | Highest-leverage agent skill |
|---|---|
| **Sanghavi** | Compliance doc checking (LC clean-rate, DGFT/EDPMS), freight-rate spike alerts, buyer-comms threading |
| **Schäfer** | OEE/scrap analysis, 8D drafting, cross-line benchmarking, Ausbildung rotation tracking |
| **Barrett** | Contemporaneous time-entry drafting, precedent suggestion, RFP drafting, deal-DD coordination |

Each becomes a **platform skill** under `skills/` — industry-specific skill packs we ship.

---

## Demo org pack — what to seed

Three one-click demo orgs for first-boot. Option on the setup wizard: *"Try a sample org before building your own."*

### A. Sanghavi Impex (Indian trading, 180)
Seed ~12 people across levels:
- L0: MD (1)
- L1: VP-Exports, GM-Compliance (2)
- L2: DGM-Europe Desk (1)
- L3: Sr. Mgr H&M Account, Manager Export Docs, Compliance Officer, AR Manager (4)
- L4: Asst Mgr LC Docs (1)
- L5: Sr. Merchandiser - Ladies Knits (1)
- L6: Jr. Merchandiser, Docs Exec, Sr. Exec RBI EDPMS (3)

8 goals, mixing VP-level ("revenue ≥ ₹650 Cr"), manager-level ("H&M OTIF ≥ 96%"), IC-level ("sample approval ≤ 7 days"). One KR each using workspace file + one URL source + one binary milestone.

Channels: `#eu-desk`, `#h&m-account`, `#compliance-edpms`, `#ar-collections`.

### B. Schäfer Präzision (German Mittelstand, 650)
Seed ~15 people:
- L0: Geschäftsführerin (1)
- L1: Prokurist / Fertigungsleiter, Prokurist / Leiter F&E, Prokurist / QM-Leiter (3)
- L2: Werkleiter, Leiter Instandhaltung (2)
- L3: 3 Meister (one per cell), Gruppenleiter Kundenqualität, Gruppenleiter Entwicklung (5)
- L4: Schichtführer Frühschicht, Senior Ingenieur (2)
- L5: Vorarbeiter Montage, Sachbearbeiter AV (2)

7 goals demonstrating OEE (workspace file), PPM (URL → customer portal), SOP milestones, Azubi rotation. Include one goal with cascade (plant OEE → cell OEEs).

Channels: `#shopfloor-zelle-1`, `#bosch-ka`, `#qm-8d-open`, `#sop-ev-valve-2026`.

### C. Barrett & Lang (NYC law firm, 580)
Seed ~15 people:
- L0: Firm Chair, CFO, CMO (3)
- L1: PG Leader - M&A, BD Director, KM Director (3)
- L3: 2 Equity Partners - M&A, 1 Equity Partner - Litigation (3)
- L4: 1 Non-Equity Partner - M&A (1)
- L6: 1 Senior Associate - M&A (Yr 7) (1)
- L7: 1 Mid-level Associate - M&A (Yr 4) (1)
- L8: 2 Junior Associates (Yr 1, Yr 2) (2)
- L-Para: 1 Senior Paralegal (1)

6 goals including:
- One **private** billable-hours goal on the junior associate (showcase `private + explicit_viewer_ids`)
- PG revenue goal on the PG Leader
- Origination goal on the Equity Partner
- BD pipeline goal on the BD Director
- KM AI-pilot goal on the KM Director
- Firm DSO goal on the CFO

Channels: `#m&a-pg`, `#km-ai-pilot`, `#rec-laterals-2026`, `#client-acme` (per major client), `#matter-acme-vs-xyz`.

### D. Nimbus Analytics (B2B SaaS Series C, 200)
Seed ~14 people:
- L0: CEO, CRO, CMO, CFO (4)
- L1: VP Sales Enterprise, VP Sales MM, VP CS, VP Marketing (4)
- L2: Director Demand Gen, Director Enterprise East, Director MM East (3)
- L4: Strategic AE, MM AE, Sr. CSM (3)
- L5: SDR (1)

8 goals including:
- Rep-level quota (private, manager-chain + CRO visible) — showcases private visibility
- Pipeline-coverage KR on an AE (URL-source to Salesforce)
- NRR goal on VP CS (URL-source)
- MQL-to-SQL conversion goal on Demand Gen Director
- CAC payback goal on CRO (computed from multiple sources)
- CMO brand-search goal (URL to Google Search Console)
- CRO ARR goal (cascade-linked to VP targets)
- Strategic-logo goal on VP Enterprise (binary milestone)

Channels: `#forecast-call`, `#deal-desk`, `#acct-acme-corp` (ABM account), `#demandgen-campaigns`, `#launch-q2`, `#cs-health-enterprise`.

### E. Luma (B2C DTC skincare, 120)
Seed ~13 people:
- L0: CEO, CMO, COO, CFO (4)
- L1: VP Growth, VP Brand, Head of E-com, Director PD, Director Wholesale (5)
- L2: Director Paid Media, Director Lifecycle, Director Creative (3)
- L3: Brand Manager, Email Lifecycle Mgr, Influencer Director (3)
- L4: Performance Specialist - Meta (1)

8 goals including:
- Blended ROAS goal on VP Growth (URL poll — Triple Whale)
- Email-revenue % goal on Lifecycle Manager (URL — Klaviyo)
- CAC target on CMO (computed from multiple sources)
- Subscription churn goal on Head of E-com
- Launch-milestone goal on Brand Manager (binary)
- Sephora sell-through on Director Wholesale (weekly workspace file)
- CSAT on Head of CX
- Brand-search volume goal on Brand Manager

Channels: `#perf-weekly-standup`, `#creative-review`, `#launch-serum-plus`, `#bfcm-2026`, `#sephora-account`, `#influencer-program`.

---

## Sales motion hypotheses by persona

(Rough guesses — validate with design partners.)

| Archetype | Economic buyer | Key sales objection | Proof-point that closes |
|---|---|---|---|
| **Sanghavi (trading)** | MD / COO | "We use WhatsApp + Tally, why change?" | Demo: "See every buyer's status in one view. Your Friday MIS takes 10 minutes to prep, not 4 hours." |
| **Schäfer (manufacturing)** | Geschäftsführer + QM-Leiter | Works Council objections on monitoring | "Agent is bonded to the employee, not management. Employees own their workspace. GDPR-clean." |
| **Barrett (law)** | Managing Partner / Firm Chair + CFO | Confidentiality, privilege, security | Self-hosted + zero outbound + per-matter ethical walls. "30 min/day saved × $650/hr × 30 associates = $2.2M/yr." |
| **Nimbus (SaaS)** | CRO (primary) + CMO (co-signer) | "We already have Salesforce + Gong + HubSpot" | Demo: "One view of quota + pipeline + NRR + CAC payback, cascaded across CRO → VP → Director → Rep. Your Monday forecast call becomes 20 minutes instead of 2 hours because the agent drafted the deal review." |
| **Luma (DTC)** | CMO (primary) + CEO/Founder | "We already live in Triple Whale + Klaviyo + Shopify" | Demo: "Your agent drafts the weekly perf review from 6 sources. Creative review channels track each brief through to shipped creative. Attribution discrepancies get surfaced, not papered over. BFCM war-room mode built in." |

---

## Open questions — things we still need to learn

- How do **holding companies** (common in India) structure visibility? A promoter running 3 entities under one umbrella — what bleeds, what stays separate?
- **Agencies / consultancies** (project-billable, partner-led) — not covered here. Close to Barrett + Luma hybrid. Add when a real design partner emerges.
- **B2C retail chains** (multi-store) — 40+ store ops, area managers, store managers — different shape than DTC. Worth a separate persona once we meet one.
- **Multi-site manufacturers** (2+ plants) — cascade rules get complex. German plants can be regional.
- **Healthcare** — compliance + care-provider roles are radically different. Skip for now unless a customer pulls us in.
- **Universities / research labs** — academic hierarchies (PI → postdoc → grad → undergrad) are yet another shape.
- **Government / PSU in India** — different entirely; scale targets measured in lakhs of people.
- **Do agents in multi-person channels cause information-leak concerns?** An agent in a goal channel with 5 humans is running inference on mixed context. Need policy.
- **How do firms with unionized workforce** (US manufacturing, parts of UK/Germany) treat goal visibility? Union contracts may restrict.

---

## Change log

- **2026-04-22** — initial draft. Three archetypes (Sanghavi, Schäfer, Barrett & Lang). Twelve cross-persona design implications captured. Demo-org pack proposed. Open questions seeded.
- **2026-04-22 (pm)** — added Persona 4 (Nimbus Analytics · B2B SaaS Series C · $35M ARR · ~200 people) and Persona 5 (Luma · B2C DTC skincare · $45M rev · ~120 people). New sales/marketing-driven org depth. Updated archetype summary table. Added Demo orgs D (Nimbus) + E (Luma). Added 2 sales-motion rows. Flagged new primitives that surface from these personas: campaign as first-class unit (DTC), account-based channels (SaaS ABM), external-collaborator person-type (DTC), attribution-source transparency (DTC), peak-season mode (DTC), pod/matrix team model (SaaS), commission-linked goal audit (SaaS), formula-backed KRs with multiple sources (both).
