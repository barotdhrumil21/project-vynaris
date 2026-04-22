---
name: build-mini-app
description: Build a small self-contained utility (script, dashboard, or tool) that your person can run to help their work. Use when a problem is solvable with ~50-300 lines of Python.
---

# Build a mini-app

## When to use
When the work is repetitive, is likely to recur, or has a clear input→output. Examples: a deduper, a cohort report, a scraper, a scoring function.

## Steps

1. **Define the interface.** What goes in, what comes out? Write it to `private/spec-<slug>.md` in 5 lines max.
2. **Write the code.** Single Python file at `public/<slug>.py`. Use only stdlib unless something complex needs pandas. Include:
   - A docstring at top explaining usage
   - `if __name__ == "__main__":` entry
   - Clear CLI via argparse if appropriate
   - A smoke-test example at the bottom (commented `# example:`)
3. **Test it.** Use `code_exec` to run it with a realistic input. Capture output. If it fails, fix. Don't hand the person broken code.
4. **Document.** A short `public/<slug>.md` with: what it does, how to run, example output, limitations.
5. **Post to feed.** "Shipped <name>. Run with `python <slug>.py <args>`. Tested on <input>. <1-line result>."

## Anti-patterns
- Don't over-engineer. No config files, no classes where functions work, no DI frameworks.
- Don't pretend it's production-grade. Call out edge cases you haven't handled.
- Don't use 3rd-party libs without asking unless they're universal (requests, pandas, numpy).
