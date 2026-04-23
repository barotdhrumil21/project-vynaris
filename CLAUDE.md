# Vynaris — Engineering Rules

These rules are load-bearing. Break them only with a written reason in the PR/commit.

## 1. Minimum lines of code is a first-class metric

Fewer lines beats cleverness. Fewer lines beats premature structure. **But never beats readability.** If two equally readable options exist, pick the shorter one. If the shorter one is only clear to you today, pick the longer one.

Concretely:
- Before writing a helper, ask: "Is this used more than twice?" If no, inline it.
- Before adding a class, ask: "Does this hold state, or am I making a namespace?" If namespace, use a module.
- Before adding a layer (service-over-service, wrapper-around-wrapper), ask: "What does removing it break?" If nothing, don't add it.
- Before adding config/flags, ask: "Is anyone going to flip this in the next month?" If no, hardcode it.
- Deleting code is progress. Count lines removed as a win in commit messages when meaningful.

Shape targets (not hard caps — blow through them with a reason):
- A function > 40 lines is suspect. > 80 is a bug.
- A file > 400 lines is suspect. > 800 needs a split with a clear boundary.
- A function signature > 5 positional args is usually a struct in disguise.

## 2. Test-driven, Uncle Bob's three laws

For core primitives — agent tools, services (`vynaris/services/*`), model invariants, data transforms — follow the three laws:

1. **Don't write production code until you have a failing test.**
2. **Write only enough test to fail** (compile errors count).
3. **Write only enough production code to pass the current failing test.**

Red → Green → Refactor. Refactor only on green. Commit on green.

Where TDD doesn't apply cleanly (and when to relax):
- **HTML templates / CSS / visual layout** — verify in the browser, capture a screenshot in the PR.
- **Prompt content & system prompts** — evaluate by running the agent end-to-end; don't unit-test prose.
- **Throwaway spikes** — mark them `spike/` in the branch name and throw them away; don't promote untested spike code into `main`.

Everything else: test first.

Test layout: `tests/` mirrors `vynaris/` one-to-one. `tests/unit/` for pure functions, `tests/integration/` for DB/HTTP boundaries. Prefer integration tests against a real Postgres (docker-compose already provides one) over mocks — mocked integration tests drift from reality and lie to you.

## 3. Clean Code, enforced

- **Single Responsibility.** A function does one thing. If its name needs "and", split it.
- **Naming is the API.** Spend time on names — `ensure_workspace`, `get_or_create_dm`, `record_pending`. Bad names rot. Renames are cheap; debugging bad names isn't.
- **No comments that restate the code.** Comments explain *why*, not *what*. If the why is obvious, write no comment.
- **No dead code, ever.** Unused imports, unused params, commented-out blocks, `TODO(me)` with no date — delete. Git is the archive.
- **No speculative generality.** No `options: dict` parameter "for later". No `BaseFoo` with one subclass. No plugin systems without two plugins.
- **Levels of abstraction don't mix.** A function either orchestrates (calls other functions) or does work (manipulates data). Not both in the same body.

## 4. Architecture — keep the current shape

The layers that exist are the layers that exist. Don't invent new ones.

```
vynaris/
  agent/       — Claude SDK runtime, tools, system prompt, skill loader
  db/          — SQLAlchemy models, session, seed, bootstrap
  services/    — business logic; pure-ish functions taking (db, *args)
  web/         — FastAPI routes, templates, static, deps
  adapters/    — (new) external channel inbound/outbound (Discord, Telegram, WhatsApp, ...)
```

Rules of travel:
- **Routes call services. Services call the DB. Agent tools call services. Adapters call the agent manager + a send() shim.**
- Routes do not touch `db.models` except for the bare query they own. Non-trivial logic moves to `services/`.
- Templates do not call services. They render what the route hands them.
- `db/models.py` is data, not behavior. No methods beyond `@property` for trivial display helpers.
- Agent tools are thin: validate args → call a service → return `_ok`/`_err`. No business logic inline in `tools.py`.
- **One transport abstraction.** External channels go through `adapters/`, not ad-hoc httpx calls in routes or services.

## 5. Anti-slop rules

These exist because LLM-assisted codebases drift toward bloat. Hold the line.

- **No backwards-compat shims for code that hasn't shipped.** Rename it, update the callers, move on.
- **No try/except around impossible cases.** If the DB guarantees it, trust it. Validate at edges (HTTP input, external API responses), not inside pure functions.
- **No fallback values masking real failures.** `value or 0` hides bugs. Raise, or return `None` and handle it explicitly upstream.
- **No "helper" files named `utils.py`, `helpers.py`, `common.py`.** Put the function where it belongs. If it has no home, you haven't thought hard enough.
- **No re-exports.** One canonical import path per symbol.
- **No feature flags for one-shot migrations.** Do the migration.
- **No commented-out alternate implementations.** Git stores those.
- **No `from x import *`.** Ever.
- **No `Any` when a concrete type fits.** `dict[str, Any]` is allowed at JSON boundaries only.
- **No silent drift from existing patterns.** If adding a new service, it looks like the existing services. Consistency beats local optimization.

## 6. Change discipline

- One concern per commit. "fix bug + refactor" is two commits.
- Commit message names the *why*. The diff is the *what*.
- Before declaring done: run the app, exercise the feature you changed, verify it actually works. Type-check pass ≠ works.
- If a test suite exists and you changed code in its scope, run it. If no test exists for the code you're changing, write one before changing (see §2).

## 7. When rules conflict

Readability > brevity. Correctness > readability. Simplicity > cleverness. Shipping the demo > theoretical purity — but shipping slop is worse than not shipping.

If you find yourself arguing for an exception, write the exception into this file with the reasoning, or don't take it.
