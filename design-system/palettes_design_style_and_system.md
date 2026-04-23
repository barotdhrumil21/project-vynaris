# Vynaris Design System — Instrument (engineered-serious)

> Canonical reference for the Vynaris UI. Mirrors `palettes.html` 1:1.
> Voice: **a control plane for agentic operations.** Cool paper, grotesque display, one cobalt light.

---

## 0. Philosophy

Six rules, in priority order. When they conflict, earlier wins.

1. **The product is the agent.** Every screen is the surface an agent surfaces *through*. The layout exists to make an agent's state — thinking, blocking, shipped — legible at a glance.
2. **Numbers are the point.** KRs, rates, budgets, latencies, costs — numerals carry the narrative. Give them weight, tnum, a tick rule, and room to breathe.
3. **Cobalt is a single light, not a paint.** `#1F4FD9` only appears when a human must act: primary CTAs, "blocking" badges, focus rings, links. Never for decoration, tags, nav, or "new" labels.
4. **Rules, not cushions.** Hierarchy comes from hairlines and contrast. Shadows are reserved for dialogs.
5. **Mono is the infra voice.** IDs, timestamps, run IDs, tool names, costs, file paths — anything a machine would recognize — renders in JetBrains Mono.
6. **Earned density.** Real artifacts (tool trace with latency + cost, policy diff inline, budget meter, audit log) over filler.

---

## 1. Foundations

### 1.1 Color tokens (light)

| Token | Hex | Role |
|---|---|---|
| `--bg` | `#FAFAF9` | Page background. Warm off-white. |
| `--surface` | `#FFFFFF` | Cards, panels, sheets. |
| `--surface-2` | `#F4F4F2` | Insets, table headers, table hover, subtle fills. |
| `--surface-3` | `#EFEFEC` | Switch track off-state. |
| `--border` | `#E6E5E0` | Hairlines between sections. |
| `--border-strong` | `#D6D5CF` | Control borders, focusable edges. |
| `--ink` | `#0B0B0A` | Primary text, numerals, dark buttons. |
| `--ink-2` | `#2E2E2B` | Body text. |
| `--ink-3` | `#6B6B65` | Meta, captions, mono labels. |
| `--ink-4` | `#9C9C94` | Placeholders, dividers in breadcrumbs. |

### 1.2 Accent — cobalt (single source)

| Token | Hex | Use |
|---|---|---|
| `--accent` | `#1F4FD9` | Primary CTA bg, `blocking·you` badge, focus ring, links. |
| `--accent-hover` | `#1840B8` | `:hover` on primary. |
| `--accent-soft` | `#E8EEFC` | Highlight cells (e.g. "asked Maya" row in audit), inline chip bg. |
| `--accent-ink` | `#143899` | Text on `accent-soft`. |

**Rule:** one cobalt decision per screen. If two things are cobalt in the same card, one is wrong.

### 1.3 Signal colors (narrow, muted)

| Role | Solid | Soft | Use |
|---|---|---|---|
| `success` | `#0E7B3E` | `#E3F1E8` | `on-track`, `ok`, shipped runs, green dots. |
| `warn` | `#B45309` | `#FBF1DE` | `drifting`, `near target`, auth expiring. |
| `danger` | `#B42318` | `#FBE6E2` | `off`, `failed`, rate-limited, retroactive warnings. |

Never mix cobalt and a signal color inside the same card — status uses signal, decisions use cobalt.

### 1.4 Typography

Three families, three jobs.

| Family | Role |
|---|---|
| **Space Grotesk** (500 weight) | Display, H1, H3, KR numerals. Negative letter-spacing (`-0.025em` → `-0.035em`). |
| **Inter** (400/500/600) | Body, H2, labels, form copy. `font-feature-settings: 'cv11','ss01'` for disambiguated glyphs. |
| **JetBrains Mono** (400/500) | IDs, timestamps, tool names, run IDs, costs, shortcuts, code. `font-feature-settings: 'tnum','lnum'`. |

**Scale** (px / line-height / letter-spacing):

| Class | Size | LH | Tracking | Weight | Family |
|---|---|---|---|---|---|
| `.t-display` | 30 | 1.08 | -0.035em | 500 | Grotesk |
| `.t-h1` | 22 | 1.20 | -0.025em | 500 | Grotesk |
| `.t-h3` | 16 | 1.25 | -0.02em | 500 | Grotesk |
| `.t-h2` | 14 | 1.35 | -0.005em | 600 | Inter |
| `.t-body` | 14 | 1.55 | — | 400 | Inter |
| `.t-sm` | 13 | 1.50 | — | 400 | Inter |
| `.t-xs` | 12 | 1.45 | — | 400 | Inter |
| `.t-meta` | 12 | — | — | 400 | Inter |
| `.t-label` | 13 | — | — | 500 | Inter |
| `.t-mono-label` | 11.5 | — | 0.02em | 400 | Mono (lowercase) |
| `.sec-lbl` | 10.5 | — | 0.09em | 500 | Mono (UPPERCASE) |

KR numerals override scale: display-size (30–44px) Grotesk 500, with `.num` (`font-variant-numeric: tabular-nums`).

### 1.5 Spacing

4px grid. Use `4 / 8 / 12 / 16 / 24 / 32 / 48`. Nothing off-grid. Section gap is 3.5rem (`py-14`), card padding defaults to 16–24px, inset padding 10–12px.

### 1.6 Radius

| Token | Value | Use |
|---|---|---|
| `--r-sm` | 5px | Chips, badges, buttons, inputs. |
| `--r-md` | 7px | Cards, panels, tables. |
| `--r-lg` | 10px | Sheets, dialogs, the in-context frame. |

### 1.7 Elevation

Three levels. No free-floating drop shadows.

1. **Hairline** — `1px solid var(--border)`. Default surface separation.
2. **Strong** — `1px solid var(--border-strong)`. Controls and focusable edges.
3. **Inverted** — ink surface + light text. Dark buttons, the avatar ink tile, code blocks.

Shadow exception — **dialogs only**:
```css
box-shadow: 0 24px 48px rgba(11,11,10,.12), 0 2px 6px rgba(11,11,10,.06);
```

---

## 2. Signature treatments

Three utility classes carry the "engineered" feel. Use them sparingly — overuse is decoration.

### 2.1 Tick rail — under numerals

```css
.tick-rail {
  background-image: linear-gradient(to right, var(--border-strong) 1px, transparent 1px);
  background-size: 8px 100%;
  background-repeat: repeat-x;
  background-position: bottom;
}
```
A ruler under the measurement. Applied to any large numeral (KR values, budget counters).

### 2.2 Corner marker — hairline nick

```css
.corner { position: relative; }
.corner::after {
  content: ""; position: absolute; top: 0; right: 0;
  width: 10px; height: 10px;
  border-top: 1px solid var(--border-strong);
  border-right: 1px solid var(--border-strong);
  border-top-right-radius: var(--r-md);
}
```
Quiet "engineered tell" on surfaces that matter (skill cards, tip cards). Never on every card.

### 2.3 Crosshatch — drafting weave

```css
.crosshatch {
  background-image:
    linear-gradient(135deg, transparent 49.5%, rgba(11,11,10,0.03) 50%, transparent 50.5%),
    linear-gradient(45deg,  transparent 49.5%, rgba(11,11,10,0.03) 50%, transparent 50.5%);
  background-size: 6px 6px;
}
```
Low-contrast diagonal weave. Applied to tip/note cards to flag "drafting paper." In dark mode, the lines flip to `rgba(255,255,255,0.03)`.

---

## 3. Controls

### 3.1 Buttons

Base shape: 30px tall, 5px radius, 13px Inter 500, 6×12 padding, `gap: 6px` for icon+label.

| Class | When |
|---|---|
| `.btn` | Default — neutral surface, strong border. |
| `.btn-primary` | Cobalt. One per screen. Has inset white highlight + cobalt glow shadow. |
| `.btn-dark` | Ink surface, white text. Routines, run-agent actions. |
| `.btn-ghost` | Transparent. Tertiary (Snooze, Mute, Cancel). |
| `.btn-danger` | `#B42318` surface. Revoke, delete, irreversible. |
| `.btn-sm` | 26px tall, 12px font. Dense rows, KR cards. |
| `.btn-icon` | 28×28, centered, 4px padding. SVG 14×14. |

**Split button:** inline-flex, inner vertical border `rgba(255,255,255,.25)` on cobalt; outer radii zeroed on the seam.

**Disabled:** `opacity: .45; pointer-events: none`. No new color.

### 3.2 Inputs

```css
.input, .textarea, .select {
  background: var(--surface);
  border: 1px solid var(--border-strong);
  border-radius: var(--r-sm);
  padding: 7px 10px; font-size: 13px;
}
.input:focus {
  outline: none;
  border-color: var(--accent);
  box-shadow: 0 0 0 3px rgba(31,79,217,.12);
}
```
Placeholders in `--ink-4`. Textareas resize vertical, min-height 72px. "Chip-inside-input" pattern (e.g. Owner picker) uses `padding: 5px 8px` and inline avatar.

### 3.3 Checkboxes, radios, switch

- **Checkbox** — 16×16, 3px radius. On-state: cobalt fill, white check drawn as `border-left + border-bottom` rotated −45°.
- **Radio** — 14×14 circle. On-state: cobalt border, 6×6 cobalt inner dot.
- **Switch** — 28×16 pill. Off: `surface-3` track. On: cobalt track, 12×12 white thumb with 1px shadow.

### 3.4 Badges / chips

```css
.badge {
  padding: 2px 7px; border-radius: 5px;
  font: 500 11.5px/1 'JetBrains Mono';
  letter-spacing: 0.01em; white-space: nowrap;
}
```
Variants: `.badge-neutral`, `.badge-ghost`, `.badge-success`, `.badge-warn`, `.badge-danger`, `.badge-accent` (solid cobalt, white text), `.badge-accent-soft` (light cobalt tint).

Dot prefix (`<span class="dot">`) — 6×6 round, inherits the variant's signal color. Used on status badges.

### 3.5 Keyboard shortcuts

```css
kbd, .ring-kbd {
  font: 11px/1.4 'JetBrains Mono';
  padding: 1px 5px; border-radius: 4px;
  background: var(--surface-2);
  border: 1px solid var(--border-strong);
  color: var(--ink-3);
}
```
Always mono. Always framed. Never used decoratively — only on rows that actually have shortcuts.

### 3.6 Toasts

Three variants stacked right-rail:

1. **Accent** — left inset `3px` cobalt + cobalt icon tile. Reserved for "agent needs you." Contains 2 CTAs (Review / Snooze).
2. **Success** — `success` border + `success-soft` background. Auto-dismiss candidate.
3. **Warn** — `warn` border + `warn-soft` background. System-health (auth expiring, connector drift).

### 3.7 Avatars

- **Circle**, `w-5/6/7/8` grid place-items-center.
- Initials in 10–11px Inter 600.
- Colors are role-coded across screens — Priya `#1F4FD9`, Maya `#0E7B3E`, Nikhil `#B45309`, Shruti `#2E2E2B`, Aditi `#B42318`. Use role + matching initial consistently.
- **Agent avatar** — ink-filled rounded square (not circle) with mono initial `A`. A `pulse` ring signals live state.

```css
@keyframes pulse-ring {
  0%   { box-shadow: 0 0 0 0 rgba(31,79,217,.45) }
  70%  { box-shadow: 0 0 0 6px rgba(31,79,217,0) }
  100% { box-shadow: 0 0 0 0 rgba(31,79,217,0) }
}
```

---

## 4. Agent surface

The central pattern. Three explicit states, one trace table, one skill card, one permissions grid.

### 4.1 Agent states

| State | Tell | Badge | Border |
|---|---|---|---|
| **Thinking** | Blinking `…` dots after italic sentence + ongoing tool rows. | `badge-ghost · thinking` | default hairline |
| **Blocking** | `inset 3px 0 0 var(--accent)` rule on the left; `blocking · you` cobalt badge. | `badge-accent` | `accent` |
| **Shipped** | `07:18 · 42s · $0.08` meta, attached artifact chip, Open/Mute CTAs. | `badge-success` | default hairline |

**Thinking dots:**
```css
@keyframes blink { 0%,80%,100% {opacity:.25} 40% {opacity:1} }
.dot-think > span {
  display:inline-block; width:4px; height:4px;
  background: var(--ink); border-radius: 50%;
  margin: 0 1.5px; animation: blink 1.4s infinite both;
}
.dot-think > span:nth-child(2) { animation-delay: .2s }
.dot-think > span:nth-child(3) { animation-delay: .4s }
```

### 4.2 Tool trace

Grid: `[24px 110px 1fr 70px 80px]` — `# · tool · args→result · status · elapsed`. Mono 12px throughout.

- Header row: ink-3.
- OK rows: `.surface-inset` (F4F4F2 bg, hairline border), tool name ink+500, args ink-2.
- Failed row: `danger-soft` bg, full `danger` border, every cell in `danger`. No ambiguity.

Header strip above the table carries `sec-lbl` + a summary badge (`ok · 842ms · $0.04`).

### 4.3 Skill card

Corner-marked card. 9×9 cobalt icon tile (star glyph). Title `t-h3`, version in ghost badge, description `t-sm`. Bottom row: 4 ghost badges for `input · output · tools · duration`.

### 4.4 Permissions grid

Checkboxes + mono labels + right-aligned scope meta (`always`, `workspace only`, `ask each time`, `L2+ approval`). One row per tool surface the skill touches.

---

## 5. Data patterns

### 5.1 KR card

```
┌─────────────────────────────────┐
│ default_rate            [off]   │  ← sec-lbl + badge
│                                  │
│  3.9 / 3.2%                     │  ← display 38 Grotesk + tick-rail
│  ───────────                    │
│                                  │
│  ╲╱╲╱╲╱╲ spark                  │  ← 120×32 polyline
│                                  │
│  ▲ +0.2pp · 12w trend           │  ← mono meta
└─────────────────────────────────┘
```
Sparkline: `viewBox="0 0 120 32"`, `stroke-width: 1.4`, stroke matches the status signal (`danger`, `ink`, `success`). Optional dashed target line at `y=14`.

### 5.2 Table

```css
.tbl th {
  font: 500 10.5px/1 'JetBrains Mono';
  text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--ink-3); background: var(--surface-2);
  padding: 9px 14px; border-bottom: 1px solid var(--border);
}
.tbl td { padding: 10px 14px; border-bottom: 1px solid var(--border); }
.tbl tr:hover td { background: var(--surface-2); }
.tbl tr:last-child td { border-bottom: 0; }
```
First column is a 24px checkbox cell. Numeric cells use `.num` class. Timestamps right-aligned and mono. Avatar + name clump in the Person cell.

### 5.3 Bar (horizontal progress)

```css
.bar { height: 5px; background: var(--surface-2); border-radius: 999px; border: 1px solid var(--border); overflow: hidden; }
.bar > span { display: block; height: 100%; background: var(--ink); border-radius: 999px; }
```
Variants: `.bar-acc` (cobalt), `.bar-go` (success), `.bar-warn` (warn), `.bar-bad` (danger). Default fill is ink — use signal only when the bar *is* a signal.

### 5.4 Chart (12-week bars)

- SVG `viewBox="0 0 300 140"`, 12 bars at x=8+24i, width=12.
- Gridlines at y = 30/60/90/120 in `--border` 0.6px.
- Target line: dashed ink 0.8px at target y with inline mono label.
- Tail bars flip color (`ink → warn → danger`) as values drift.
- Head circle — 3px radius, `surface` fill + 1.5px danger stroke — marks the current value.

### 5.5 Audit log

Grid `[70px 90px 1fr 60px]` — timestamp · action · description · metadata. Mono 12px.

Highlighted rows: wrap the row `div` in `background: var(--accent-soft); border-radius: 3px` for "human-in-loop asked" events, `--warn-soft` for auth/health.

Header: `immutable · signed` in the right corner, ink-3 mono 10.5px.

---

## 6. Shells

### 6.1 Command bar (⌘K)

- Outer frame: 1px `border-strong`, `0 8px 24px rgba(11,11,10,.08)` shadow, `var(--r-md)` radius.
- Input row: `>` prompt + text input + `esc` kbd.
- Sectioned results: mono section labels (`Goals · 2`, `Skills · 1`, `People · 1`).
- Active row: `background: var(--accent-soft); color: var(--ink)` with cobalt arrow glyph.
- Footer row: `surface-2` with keyboard hints (`↑ ↓ navigate · ↵ open · ⌘↵ run skill`).

### 6.2 Empty state

- Centered, min-height 280px.
- 48×48 dashed ink-3 square icon.
- `t-h3` headline + `t-sm` ink-3 body (max-w 340px).
- Primary + secondary CTA pair.
- Footer kbd hints with hairline divider above.

### 6.3 Modal / dialog

- Radius 10px.
- `border-strong` 1px.
- Shadow: `0 24px 48px rgba(11,11,10,.12), 0 2px 6px rgba(11,11,10,.06)`.
- Three-part: header (title + ✕), body (form), footer (`surface-2` bg with kbd hint + Cancel/Confirm).
- Mounted over a `surface-2` page-cover to tell it apart.

### 6.4 Connector tile

```
┌────────────────────┐
│ crm-api       ●    │  ← mono name + status dot
│ auth expires 2d    │  ← meta (colored when warn/danger)
└────────────────────┘
```
2-column grid of `.surface-inset` tiles. Empty slot is `border-style: dashed` + `+ add connector`. Status dot colors: success/warn/danger — never cobalt.

---

## 7. In-context scene (the whole system under one goal)

Architecture, top-to-bottom:

1. **Breadcrumb** — mono 11.5px, `goals / q3-credit / G-0142 · synced 2m ago`.
2. **Goal hero** — 3/9 split. Left: owner, cycle, status, visibility. Right: `t-display` headline with cobalt-highlighted target numbers, body, CTA row.
3. **KR rail** — 3-column card with divided cells. Each KR = label + status badge + 36px Grotesk numeral on tick-rail + target + delta.
4. **Agent card** (2/3) — header (avatar + run_id + `needs decision` badge), body with `t-h1` question, tool trace, policy diff, action row (Approve / View memo / Snooze + impact meta).
5. **Sidebar** (1/3) — tip (crosshatch + corner), today's events timeline, budget meter (display numeral + bar-acc).
6. **Composer** — bottom-pinned row: `@agent` chip, input, ⌘ ↵ kbd, Send primary.

### 7.1 Policy diff (inline)

```html
<pre class="mono text-[12px]" style="background:var(--surface)">
  <span style="color:var(--success);background:var(--success-soft);
               display:block;padding:1px 4px;margin:0 -4px">
    + if cibil < 700 and channel == "marketplace_x": reject(...)
  </span>
</pre>
```
Added lines: full-bleed `success-soft` background + `success` text. Removed: `danger-soft` + `danger` (mirror). No syntax highlighting — structure carries meaning.

---

## 8. Dark mode

Scoped via `.dark-wrap` — re-declares the CSS custom properties. **No components change shape.** Only tokens flip.

```css
.dark-wrap {
  --bg:           #0C0D11;
  --surface:      #14161B;
  --surface-2:    #1B1E25;
  --surface-3:    #22252D;
  --border:       #23262D;
  --border-strong:#2E323B;
  --ink:          #EEEEF0;
  --ink-2:        #C7C8CE;
  --ink-3:        #8A8C94;
  --ink-4:        #5F6069;
  --accent:       #5A86F5;  /* lifted for dark */
  --accent-hover: #7298F7;
  --accent-soft:  #1A2343;
  --accent-ink:   #B2C7FB;
  --success:      #3FAF6C;  --success-soft: #0F2B1B;
  --warn:         #D1913E;  --warn-soft:    #2E2213;
  --danger:       #E06251;  --danger-soft:  #2E1614;
  background: var(--bg); color: var(--ink);
}
.dark-wrap .crosshatch { /* white diagonals instead of ink */ }
.dark-wrap .tick-rail  { /* border-strong rail adapts via token */ }
```

**Cobalt lifts** from `#1F4FD9` → `#5A86F5` for perceived contrast parity. The ratio cobalt-to-background stays constant in both modes.

---

## 9. Rules — do / don't

### ✓ Do

- **Accent discipline.** Cobalt = a human must act. One per screen.
- **Numerals with weight.** Grotesk 500, tnum, negative tracking, on a tick rail. Target sits in ink-3.
- **Mono for structure.** IDs, timestamps, tool names, run IDs — mono. Anything a machine names.
- **Rules > shadows.** Hairlines carry hierarchy. Shadows only on dialogs.
- **Earned density.** Latency + cost on every trace. Inline diffs. Budget meters. Real.
- **Status via signal.** Success/warn/danger for state. Not decoration.

### ✕ Don't

- **No accent bloat.** Never cobalt on "new", tags, nav, secondary CTAs, category pills.
- **No decorative Grotesk.** Grotesk is for structure (headlines, KR numerals). Never for body prose, greetings, or chatty copy.
- **No mixed signals.** Don't put cobalt and a status color on the same card.
- **No shadow padding.** If a card needs a shadow to separate from another, the layout is wrong — add a hairline instead.
- **No off-grid spacing.** 4px grid holds. If you need 15, use 16.
- **No emoji.** Ever. Mono glyphs (`▾ ✕ ↵ ↑ ↓ / >`) only.

---

## 10. Implementation notes

### 10.1 Stack

- **Tailwind** via CDN (`<script src="https://cdn.tailwindcss.com">`) for layout utilities.
- **Custom CSS** for all tokens, typography, and composed components (see `palettes.html` `<style>` block). Tailwind does not own color — our tokens do.
- **Google Fonts** — `Space Grotesk` (400/500/600/700), `Inter` (400/500/600/700), `JetBrains Mono` (400/500/600).
- **Icons** — inline SVGs, 12–22px, `stroke-width: 1.2–1.6`, `stroke="currentColor"`. No icon fonts, no libraries.

### 10.2 Font activation

```css
html, body { font-family: 'Inter', system-ui, sans-serif;
             font-feature-settings: 'cv11','ss01'; }
.display { font-family: 'Space Grotesk', system-ui, sans-serif;
           letter-spacing: -0.025em; }
.mono    { font-family: 'JetBrains Mono', ui-monospace, monospace;
           font-feature-settings: 'tnum','lnum'; }
.num     { font-variant-numeric: tabular-nums;
           font-feature-settings: 'tnum','lnum'; }
```

### 10.3 Composition primitives

```css
.surface       { background: var(--surface); border: 1px solid var(--border);
                 border-radius: var(--r-md); }
.surface-inset { background: var(--surface-2); border: 1px solid var(--border);
                 border-radius: var(--r-sm); }
.hairline        { border-color: var(--border); }
.hairline-strong { border-color: var(--border-strong); }
```
Compose with Tailwind padding/flex/grid. Example:
```html
<div class="surface p-5 corner">
  <div class="sec-lbl mb-3">Skill · cohort_drilldown</div>
  ...
</div>
```

### 10.4 What lives in HTML vs CSS

- **HTML/Tailwind** — layout (grid, flex, gaps, padding, widths), one-off colors via `style="..."`.
- **CSS (tokens + classes)** — every color that could vary by theme, every repeated shape (`.btn`, `.badge`, `.surface`, `.tick-rail`), every animation.

If a color appears twice, it's a token. If a shape appears twice, it's a class.

### 10.5 File of record

`design-system/palettes.html` — runnable, single-file, no build step. Every claim in this doc is verifiable there. When tokens change, change both.

---

*Vynaris · Instrument — engineered-serious · component sheet v0.3 · 2026-04-23*
