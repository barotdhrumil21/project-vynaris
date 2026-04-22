# Vynaris — Build Plan & Demo Scripts

> **Companion to `target customer profiles and user stories.md`.** This doc is action-oriented: locked scope decisions, demo scripts for presentations/investor conversations, Claude SDK usage plan, and the next-batch build queue.
>
> **When reading this after a context clear:** skip to the *Current state* section first, then the *Next action*, then come back for demos.

---

## Scope decisions (locked)

### Cut now — don't build
- **Threads on messages.** Slack's worst UX. Defer until begged for.
- **External integrations** (Slack, Teams, email-in, Salesforce, etc.). Vynaris *is* the workspace, not a connector-router. Re-evaluate only when a design partner makes it a dealbreaker.
- **Multi-tenant cloud SaaS.** Self-hosted single-tenant only for now. 2027 problem.
- **Native mobile apps.** Bare-minimum mobile web (responsive, works on a phone). No React Native, no App Store.

### Keep and deepen
- **Per-persona taxonomies and starter packs.** Specialization beats generalization. Each persona gets its own skill pack, demo seed, goal templates, channel templates, data-source patterns.
- **Claude Agent SDK native muscles** — managed agents, loops (scheduled runs), routines (skill-based procedures). See §Claude SDK usage below.
- **Local-first / self-hosted / own-chat-UI.** The whole pitch.

### Ship first (unblock everything else)
- **Data-source reality.** Workspace-file KR, URL KR, formula KR — until these work, every goal is still status theater.
- **Core org primitives.** Level, team-membership, private-to-viewer-list, watcher without ownership, external-collaborator.
- **Per-persona demo packs** on first boot.

---

## Per-persona taxonomy — the specialization bet

Each of the 5 personas gets its own specialized pack. Picked on setup wizard; can be added later.

| Persona | Skill pack (markdown skills loaded for agents) | Goal templates | Channel templates | KR data-source patterns |
|---|---|---|---|---|
| **Sanghavi (trading)** | LC-discrepancy-drafter · EDPMS-reconciliation · freight-spike-detector · buyer-compliance-audit · Friday-MIS-builder | "OTIF ≥ 96% per buyer" · "Clean LC rate ≥ 85%" · "DSO < 68 days" · "Zero EDPMS >90d" | per-buyer-account (parent) + sub-channels · #compliance-edpms · #ar-collections · #shipment-ops · #friday-mis | Excel trackers · ICEGATE portal · bank LC status · DGFT portals |
| **Schäfer (manufacturing)** | 8D-drafter · OEE-analyzer · shift-handover-summarizer · audit-prep · Ausbildung-rotation-tracker | "Cell OEE ≥ 82%" · "PPM ≤ 20 per customer" · "SOP by date (milestone)" · "8Ds closed <15d" | per-cell-shopfloor · #bosch-ka · #qm-8d-open · per-SOP-project | MES CSV dumps · CAQ/Babtec exports · customer-portal polling |
| **Barrett (law)** | time-entry-drafter · precedent-finder · RFP-drafter · DD-coordinator · Chambers-submission-builder | "PG revenue $X" · "1,950 billable hrs (private)" · "Originations ≥ $Y" · "3 laterals closed" · "Matter X SOP" | per-matter + per-PG + per-client · #pg-m&a · #km-ai-pilot | Elite CSV · iManage metadata · WIP reports |
| **Nimbus (SaaS)** | forecast-call-preparer · deal-review-drafter · pipeline-drift-detector · QBR-preparer · competitive-battlecard | "Quota $X (private)" · "Pipeline coverage 4×" · "NRR 115%" · "CAC payback ≤18mo" · "MQL→SQL ≥25%" | per-opp-acct (ABM) · #forecast-call · #deal-desk · #cs-health · #demandgen-campaigns | Salesforce URLs · Gong summaries · HubSpot/Marketo · Stripe |
| **Luma (DTC)** | perf-weekly-drafter · creative-brief-writer · attribution-reconciler · BFCM-warroom-assembler · influencer-outreach | "Blended ROAS ≥2.1" · "Email = 26% of rev" · "Sub churn <4%" · "CAC ≤ $48" · "Launch date (milestone)" | per-campaign · #perf-standup · #creative-review · #influencer-program · per-launch | Triple Whale · Klaviyo · Recharge · Meta Ads · Shopify |

**Specialization philosophy:** a generic "goal-tracking tool with agents" is everyone's 3rd priority. A "fintech credit-risk workspace with agents pre-trained on LC-compliance and cohort analysis" is a fintech's #1 priority. We lose breadth; we win depth. Phase 2 killer features are *explicitly* per-persona.

---

## Claude SDK usage — agents, loops, routines

### Managed agents (currently wired)
- One `ClaudeSDKClient` per person, kept alive in `AgentManager`.
- Person's system prompt: org context + goals + recent channel events + skills manifest.
- Tools: the 12 Vynaris primitives + skills loaded on demand (progressive disclosure).
- Workspace: file-backed (`memory.md`, `plan.md`, `todo.md` + `private/`, `public/`).

### Loops (to add — Phase 2)
Scheduled agent runs on a cadence. Driven off goal `cadence` field.

| Loop | Fires | Persona primary use |
|---|---|---|
| **Daily check-in draft** | 07:00 local | [M] shopfloor, [N] pipeline drift, [D] perf ROAS |
| **Weekly check-in draft** | Monday 09:00 | all — the Nanoclaw equivalent of "what happened last week" |
| **Month-end reporting** | last business day, 17:00 | [T] Friday MIS, [N] commit/best/pipe, [L] realization |
| **Drift-detector** | every 6h when a KR has a defined threshold | [N] pipeline coverage slipping, [D] ROAS falling, [M] scrap spiking |
| **Data-source refresh** | per-KR cadence (default daily) | all — reads workspace file / polls URL, updates `current_value` |

Implementation: single `APScheduler` in-process, enqueues agent tasks. Agent task = "load person's context + assigned skill (e.g. `weekly-checkin-draft`) + post result as a draft message the person approves."

### Routines (skill invocation pattern)
Routine = a named skill the agent invokes on demand or on schedule. Exists in `skills/` as markdown with step-by-step instructions.

Examples:
- `weekly-checkin-draft` — routine that assembles the weekly narrative for a goal
- `forecast-call-preparer` (SaaS) — routine that pulls Salesforce + Gong, drafts commit/best/pipe per opp
- `cohort-analysis` (fintech) — routine that runs code_exec to cluster defaults
- `perf-review-drafter` (DTC) — routine that pulls Triple Whale + Klaviyo, summarizes channel deltas

Routines are just **platform skills with scheduled hooks**. User can write their own routines too (personal skills).

---

## Demo scripts (role-specific)

Each demo is narrative — designed to be walked through in 60–120 seconds. WOW moment is in **bold**. What each demo proves is in the "Primitives shown" line.

---

### Demo 1 — Credit Risk Manager (Sanghavi)
**Role:** Rohan Desai · Head of Credit Risk · Sanghavi Impex · L2

**Setup on screen:**
- Goal: *"Reduce default rate on sub-50L SMB book to under 3.2% by end of Q3"*
- Open · Owner: Rohan · Due Aug 31
- 3 KRs visible as cards:
  - **Default rate (sub-50L, 90-day rolling)** — `3.9% / 3.2% target` · source: workspace `public/kpi.csv` · last updated 2h ago
  - **New-customer approval rate** — `62% / 65% target` · source: URL poll of internal CRM
  - **Policy updates shipped** — `1 / 2` · manual

**Script:**

> Rohan opens the goal channel. An agent-drafted check-in is already pinned from this morning:
>
> > **Agent's Monday check-in:**
> > Narrative: *"Default rate ticked from 3.7% → 3.9% over the past week. The regression is driven by 3 delinquencies from customers onboarded Q1, all via Marketplace X. The other acquisition channels are stable or improving."*
> > Blockers: none new
> > Next: investigate Marketplace X cohort, compare signal quality
> > KR updates: default rate 3.7 → 3.9 (workspace file)
>
> Rohan types: *"Pull the last 12 months of sub-50L defaults. Cluster by acquisition channel + credit-bureau score band. Show which combos predict default. Write the analysis to a public artifact and ping me when done."*
>
> Live in the channel, the agent:
> - Calls `fs_read` → reads `public/defaults-12mo.csv` (the CSV Rohan's team maintains)
> - Calls `code_exec` with a pandas snippet → clusters the data, prints: "Marketplace X × CIBIL 650–700 cohort: 11.4% default rate vs 3.1% portfolio avg. N = 87 loans."
> - Calls `fs_write` → `public/cohort-analysis-apr-2026.md` with the findings
> - Calls `goal_check_in` → posts to the channel with "KR update pending analyst review; added an artifact; recommending policy change."
> - **Calls `goal_ask`** → raises a question in the goal channel: *"@Rohan — should we stop underwriting Marketplace X × sub-700 CIBIL going forward, and retroactively review the 14 open loans? (Blocking — policy decision needed.)"*
>
> Rohan clicks on the question → types an answer inline → the question is marked resolved, answer visible in timeline.
>
> Rohan: *"Draft a policy memo explaining the change. Post to #compliance, mention Maya (CEO) for approval, and attach the cohort analysis."*
>
> Agent drafts memo → posts to `#compliance` with `@Maya` → **system-event in Maya's feed: "Policy change proposed by Rohan; waiting on your approval."**

**Primitives shown:**
- Structured check-ins with KR updates
- `fs_read` + `code_exec` + `fs_write` chain (agent as analyst, not chatbot)
- Artifacts tied to the goal channel
- `goal_ask` + inline resolution
- Cross-channel posting with @mention
- Goal referenced across three channels (goal + compliance + CEO feed)
- **WOW:** 12-month CSV → clustered analysis → policy memo → CEO notified — *one user prompt*

---

### Demo 2 — Performance Marketer (Luma)
**Role:** Maya Tran · Performance Marketing Specialist (Meta) · Luma · L4

**Setup on screen:**
- Goal: *"Meta blended ROAS ≥ 2.4 for April"*
- 3 KRs:
  - **Meta ROAS (rolling 7d)** — `2.1 / 2.4 target` · URL-source · Triple Whale API · *refreshed every 6 hours*
  - **CAC (new-customer, Meta-attributed)** — `$46 / $42 target` · URL-source
  - **Creative tests shipped this month** — `8 / 12` · manual

**Script:**

> Maya opens the goal channel on Monday 8am. **A drift-detector loop fired at 7am and the agent has already drafted a weekend brief:**
>
> > **Agent's weekend perf brief:**
> > Narrative: *"Meta ROAS slipped to 2.1 over the weekend — cold-audience CTR on 'clean skin' creative dropped from 1.1% to 0.6%. Creative fatigue likely. Ad set #47 is the biggest drain: $8.2K spend at 1.4 ROAS. Top performer is Serum-A carousel; scaling well."*
> > Blockers: creative team has no new hooks this week
> > Next: propose kill #47, reallocate to Serum-A, brief Riley for 3 new hooks
> > KR update: ROAS 2.3 → 2.1 (Triple Whale)
>
> Maya: *"Confirm kill #47. Reallocate that $8K to Serum-A over the next 3 days. Draft a memo to Sam explaining the move. And draft a creative brief asking Riley for 3 new hooks for the cold audience — save it to the creative-review channel."*
>
> Agent:
> - Posts `goal_check_in` approving the spend shift (manual in Meta; agent doesn't have ad-manager API write access — honest scope)
> - Drafts the memo → saves to `public/meta-reallocation-apr.md`
> - Calls `post_to_channel` → posts to `#creative-review` with the brief
> - **Calls `goal_ask` in #creative-review:** *"@Riley — can you turn 3 new cold-audience hooks for Serum in the next 48h? Blocking for Week 2 test cycle."*
> - Posts a summary to Maya's goal channel
>
> Elsewhere, Riley (copywriter) sees the mention in `#creative-review`, replies inline, resolves the question. Maya's goal timeline now shows: check-in → memo drafted → brief dispatched → Riley committed to 48h turnaround.

**Primitives shown:**
- Agent **proactively** drafts before the human opens the channel (loop + drift-detector)
- Real numbers from URL data source (Triple Whale)
- Agent-generated memo as artifact
- Cross-channel posting (goal → creative-review)
- Question primitive for cross-team unblock
- Human remains in the loop on irreversible actions (spend reallocation)
- **WOW:** Maya starts her week with the analysis already done; one prompt dispatches 3 downstream actions

---

### Demo 3 — Email Lifecycle Manager (Luma)
**Role:** Jordan Ellis · Email Lifecycle Manager · Luma · L3

**Setup on screen:**
- Goal: *"Email = 26% of total revenue this quarter"*
- KRs:
  - **Email revenue share** — `24% / 26% target` · URL-source · Klaviyo
  - **Welcome-flow open rate** — `38% / 45% target` · URL-source · Klaviyo
  - **Subscription churn (monthly)** — `4.6% / 4.0% target` · URL-source · Recharge

**Script:**

> Agent's daily loop at 7am spots: welcome-flow open rate has trended down 9pp over 2 weeks. Drift-detector fires. Agent posts to Jordan's goal channel:
>
> > **Drift alert (agent):**
> > *"Welcome-flow open rate has dropped from 47% → 38% across 2 weeks. Send frequency is unchanged. Deliverability reputation (Klaviyo inbox-placement metric) stable. Hypothesis: subject-line fatigue — 6 weeks of 'Start your Luma routine' variants. Average subject-line freshness score has dropped 40%."*
> > Recommendation: AB test 3 new subject variants on next 5K new subscribers. I've drafted options; want me to hand them to Riley?
>
> Jordan: *"Yes, hand to Riley — but first pull the 10 highest open-rate subject lines from the last 12 months from the flow. I want to see what worked historically."*
>
> Agent:
> - Reads `public/klaviyo-export-apr.csv` (workspace file updated weekly by mkt ops)
> - Runs `code_exec` to sort and filter
> - Produces a `public/top-subjects-12mo.md` artifact with the top 10 + commentary
> - Pings Jordan in-channel
>
> Jordan reviews, picks themes. Agent drafts 3 new subject variants leveraging those themes, writes a test brief (*audience · duration · success threshold · pre-registered hypothesis*) to `public/welcome-flow-test-may.md`, then **`post_to_channel`** → `#creative-review` pings Riley with a question: *"Any copy-voice objections on these 3 variants before we hand to Klaviyo?"*
>
> Over the next 2 days the question is resolved, agent notes the test is live (Jordan configured in Klaviyo — agent doesn't auto-push changes to their email tool). Agent adds a follow-up routine: *"Check results on day 5 and day 10, post to this channel."*

**Primitives shown:**
- Drift-detector loop
- Agent forms hypothesis + recommends action
- Historical analysis via workspace file
- Artifact pinned to goal
- Cross-team handoff via question + mention
- Agent schedules its own follow-up (`spawn_subtask` equivalent)
- Honest scope: doesn't push to Klaviyo directly; Jordan stays in control

---

### Demo 4 — CMO weekly perf review (Luma)
**Role:** Priya Mahajan · CMO · Luma · L0

**Setup on screen:**
- Priya opens `#perf-weekly-standup` Tuesday morning
- She has 6 goals across paid / lifecycle / brand / CX / e-com / launches
- Her agent has run a cross-goal loop over the weekend

**Script:**

> Agent posted a `check_in` to `#perf-weekly-standup` at 07:00 Tuesday:
>
> > **Agent's Tuesday weekly (CMO)**
> > **On track:** Email revenue share, brand-search volume, subscription subs count
> > **Drifting:** Meta ROAS (2.4 → 2.1 — Maya acted Mon, watching), welcome-flow open rate (Jordan running AB test, results Thu)
> > **At risk:** Serum-Plus launch date — creative review behind by 2 days; Riley flagged 3 hooks needed by Fri for perf
> > **New artifacts this week:** `public/cohort-analysis-apr-2026.md` (Rohan) · `public/top-subjects-12mo.md` (Jordan) · `public/meta-reallocation-apr.md` (Maya)
> > **Questions awaiting your call:** 1 — Sam asking whether we shift TikTok test budget forward by 2 weeks to cover Meta gap
> > **Attribution note:** Triple Whale says ROAS 2.1, Meta Ads Manager says 2.3, Shopify last-click says 2.0. Spread of 0.3 is within typical variance. Reported in the Triple Whale anchor.
>
> Priya scrolls the goal list, each goal shows `state: open`, her agent-drafted summary, current KR value vs target, drift indicators.
>
> She replies: *"Answer Sam: yes shift TikTok up. Question for you, agent — what did we ship this week, measured in artifacts + goal movements?"*
>
> Agent responds with a one-screen summary across all 6 of her goals — 4 shipped artifacts, 3 KRs moved, 2 questions resolved, 1 question open. Each line is a clickable reference to the underlying channel.

**Primitives shown:**
- **Agent operates across all the CMO's goals, not one** (cross-goal loop)
- Attribution-source transparency (Triple Whale vs Meta vs Shopify shown explicitly, not flattened)
- Aggregated question surface (she handles 6 goals in 2 minutes)
- Artifact index
- Executive mode: the agent is a chief-of-staff, not a copilot
- **WOW:** she gets a full Tuesday executive briefing without opening a single other channel

---

### Demo 5 (bonus) — M&A Senior Associate: time-entry drafting (Barrett)
**Role:** Michael Ross · Mid-level M&A Associate Yr 4 · Barrett & Lang · L7

**Setup on screen:**
- Private goal: *"2,000 billable hours + zero late entries this month"* (visible only to Michael + his manager-chain + CFO)
- Michael has 3 active matters: #2026-0142 Acme acquisition, #2026-0189 Stellar JV, #2026-0211 diligence-only
- It's Friday 4pm, he's been heads-down all week

**Script:**

> Michael opens his agent channel. Types: *"Draft my time entries for this week. Calendar + doc edits + matter-channel activity. Group by matter."*
>
> Agent:
> - Reads Michael's calendar (workspace file — Michael exports his Outlook calendar weekly)
> - Reads his NetDocuments doc-edit metadata (workspace file — firm-provided daily export)
> - Reads the last 7 days of matter-channel messages he authored
> - Cross-references each time block → matter → task description
>
> Produces a draft:
>
> > **Monday**
> > - Matter #2026-0142 (Acme) · 2.3h · Reviewed diligence reports in VDR; drafted 3 reps-&-warranties clauses; call with target counsel
> > - Matter #2026-0189 (Stellar) · 1.7h · Revised JV agreement schedule 4.2; email to partners re: tax treatment
> > - Non-billable · 0.8h · Firm training (CLE ethics)
> > [...]
>
> Michael scans. For one block he types: *"that was actually on Stellar, not Acme — I got them confused. Re-bucket."*
>
> Agent revises. Michael approves. Each line becomes a draft time entry he can paste into Elite. **The whole week's entries: 12 minutes. In the Elite-only flow, this takes 45–60 minutes on a Friday evening.**

**Primitives shown:**
- Agent reads private context (calendar + doc-edit log + channel activity)
- Aggregates across matters (matter primitive in action)
- Billable vs non-billable classification
- Owner approves, agent doesn't auto-push to Elite (respects firm policy)
- Time saved ×associate-rate = $$ story at pitch time

---

### Demo 6 (bonus) — Enterprise AE: forecast-call prep (Nimbus)
**Role:** Jake Park · Strategic AE · Nimbus · L4

**Setup on screen:**
- Goal: *"Q2 quota $300K ACV"* (private)
- KRs: Quota attainment · Pipeline coverage (currently 4.2×) · Avg deal cycle
- Monday 8am, weekly forecast call is at 10am

**Script:**

> Jake's agent ran a forecast-prep loop at 7am. Check-in is waiting:
>
> > **Agent's pre-forecast brief (Jake)**
> > **Commit (closable this quarter):** Globex ($180K) — signed LOI, legal in final review; Meridian ($80K) — verbal yes, MSA out
> > **Best case:** Atlas Group ($120K) — CFO engaged but budget freeze rumored, champion still strong
> > **Pipeline (Q3+):** 4 opps totalling $620K, all pre-qualification
> > **Risk flags:**
> > - Globex: legal review has been stalled 6 days (Gong transcript shows their associate GC mentioned "Q2 end push" — may slip to Q3)
> > - Atlas: budget freeze chatter from the Gong call 4 days ago — champion has not re-confirmed
> > **Proposed commits for the call:** Globex + Meridian = $260K, Atlas as upside. Hitting quota depends on Globex closing by May 27.
> > **Action before the call:** I drafted a note to Globex's GC to nudge final review; draft is in `public/globex-nudge.md` — want to send?
>
> Jake reads in 90 seconds, sends the draft, goes to the call. He stays with the call, not with the forecast spreadsheet.

**Primitives shown:**
- Gong-transcript ingestion (as a data source for agent context)
- Risk-flagging from cross-referenced signals (stall + verbal signal)
- Draft actions pre-prepared (nudge note)
- Agent as sales-operator-in-a-box
- **WOW pitch:** Monday forecast prep in 2 minutes, not 40 minutes

---

## Build order (summary reference)

Detailed plan lives in the conversation history and `target customer profiles and user stories.md` § Cross-persona design implications. Fast reference:

**Batch 1 — data-source reality**
Workspace-file KR (agent reads CSV on cadence, extracts value, updates KR, emits system event) · URL KR (fetches, extracts JSON/regex) · Formula KR (a ⊕ b ⊕ c from multiple sources).

**Batch 2 — onboarding viability**
Bulk people import (CSV) · Level + level_label on Person · Manager reassignment in admin UI · Demo-org picker on first boot (5 cards + blank).

**Batch 3 — org reality**
Team-memberships (`TeamMembership` model, matrix) · Private + explicit-viewer-list visibility · External-collaborator person-type · Watcher-without-ownership UI · Working-mode on Person.

**Batch 4 — pick a design partner's persona killers**
See the 5-persona starter-pack matrix in §Per-persona taxonomy. Ship whichever pack the first design partner belongs to.

**Batch 5 — loops + routines**
APScheduler in-process · loop definitions (daily check-in, weekly check-in, drift-detector, KR refresh) · skill packs wired to loops.

**Batch 6 — enterprise prep**
SSO · SOC 2 posture · audit-log views · agent permission gates on risky actions.

---

## Current state (as of this session)

### Shipped
- ✅ Password auth (bcrypt) · Setup wizard (first admin) · Invite flow (admins create people with invite URLs; users set password via `/signup/<token>`)
- ✅ Session cookies (itsdangerous, 30d)
- ✅ Channels + Messages + SSE streaming (Slack-lite)
- ✅ Channel kinds: public · private · dm · agent · **goal**
- ✅ Agent runtime (Claude Agent SDK) — works via Claude CLI subscription auth, no API key needed
- ✅ 12 tool primitives (web_search, web_fetch, fs_*, code_exec, list_channels, post_to_channel, view_my_goals, goal_check_in, goal_ask, goal_answer, kr_update, close_goal, load_skill)
- ✅ Goal v2 with KRs (name, unit, target, current, measurement_kind/config)
- ✅ Binary goal state (open/closed)
- ✅ Structured check-ins (narrative + blockers + next_steps + KR updates)
- ✅ Questions + answers (resolved_at)
- ✅ System events (goal_created, owner_changed, kr_value_changed, goal_closed)
- ✅ Goal creation requires at least one KR with a measurement source
- ✅ Reassign permissions: admin anywhere; creator within subtree; owner reports own progress only
- ✅ Light + dark theme toggle (CSS-var driven)
- ✅ 6 platform skills under `skills/` (research-topic, analyze-data, draft-document, plan-work, summarize-feed, build-mini-app)
- ✅ Workspace viewer (file browser per person)

### Not yet built (blocks most demos)
- ❌ **Workspace-file KR actually reads the file and updates current_value** — currently just a string field on the KR. Agent can't measure.
- ❌ **URL KR actually polls** — same.
- ❌ **Formula KR** — doesn't exist.
- ❌ **Loops / scheduler** — no APScheduler integration.
- ❌ **Bulk people import** — admin adds one at a time.
- ❌ **Level field on Person** — only `title` string.
- ❌ **Team-memberships / matrix** — only `manager_id`.
- ❌ **Private + explicit viewer list** — only private/team/org.
- ❌ **External collaborator type** — not modeled.
- ❌ **Working-mode** — not modeled.
- ❌ **Demo org packs** — none exist (user builds from scratch).
- ❌ **Matter primitive** (Barrett killer) · **Campaign primitive** (Luma killer) · **ABM channels** (Nimbus)
- ❌ Any of the 5 persona skill packs.

### DB state
- Live org: Dhrumil's Workspace (user's test org). 1 admin + 1 teammate. Several test goals (some stale, some current).
- Temp test passwords on both users set during earlier session (`temp-test-pw-99` / `gh-test-pw-99`) — can reset via `.venv/Scripts/python.exe -m vynaris reset-password <email>`.

### Files of interest
- `vynaris/db/models.py` — schema
- `vynaris/services/goals.py` — check-in/question/close/reassign logic
- `vynaris/agent/tools.py` — 12 MCP tools
- `vynaris/agent/system_prompt.py` — context builder (currently injects goals + recent events + skills)
- `vynaris/web/routes/goals.py` · `channels.py` — route logic
- `vynaris/web/templates/channel.html` — the main chat + goal-header UI
- `target customer profiles and user stories.md` — 5-persona reference
- `build plan and demo scripts.md` — this file

---

## Next action

**Ship Batch 1 (data-source reality).** Specifically:

1. **Workspace-file KR source.** Agent reads CSV/Excel at `measurement_config.path` on cadence; extracts the configured column/row; updates `current_value`; emits `kr_value_changed`. Cadence default: daily.
2. **URL KR source.** Agent fetches the URL; extracts via `jq`-style path for JSON or regex for text; same update pattern.
3. **Formula KR source.** `current_value = formula_expr` where formula references other KR ids by alias. Evaluate on each input change.
4. **In-process APScheduler** to drive the above. One job per KR with a cadence.

After Batch 1: goals finally update themselves from reality. That's the moment Vynaris stops being status theater and becomes a measurement system.

When you're ready, clear context and type:

> *"go batch 1 per the build plan doc. also seed a workspace file on the existing goal so I can demo the Credit Risk flow."*

That triggers: ship workspace-file KR + URL KR + formula KR + scheduler; seed a realistic CSV into one of the user's goals so Demo 1 is clickable end-to-end.

---

## Change log

- **2026-04-22 (build-plan doc)** — Initial draft. Locked cut/defer decisions (cut threads · cut external integrations · skip multi-tenant · bare-minimum mobile web · keep per-persona taxonomies · keep Claude loops/routines). 6 demo scripts drafted (Credit Risk · Performance Marketer · Email Lifecycle · CMO · M&A Associate · Enterprise AE). Build order summarized in 6 batches. Current state captured for context-clear continuity.
