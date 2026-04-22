---
name: analyze-data
description: Run quantitative analysis on a dataset using Python in a sandboxed subprocess. Use when your person asks about numbers, trends, cohorts, or distributions.
---

# Analyze data

Use this skill when the question is quantitative: "what's the trend", "how big is X", "which cohort is worst".

## Workflow

1. **Get the data.** If the person references a file, `fs_read` it. If it's a URL, `web_fetch`. If there's no data and none can be fetched, say so and ask.
2. **Plan.** Write a 3–5 line plan to `private/analysis-<slug>.md` stating: the question, what you'll measure, what a clean answer looks like.
3. **Write the script.** Use `code_exec` with a self-contained Python snippet. Prefer standard library and `csv`, `statistics`. If pandas is installed, fine. Always print the result and any caveats.
4. **Sanity-check.** Does the magnitude make sense? Did you drop rows? Are there nulls? Report limitations honestly.
5. **Save artifact.** Write a short finding to `public/analysis-<slug>.md`: question, method (1–2 lines), result (numbers + interpretation), caveats.
6. **Post to feed** with the headline and one number. Link the artifact.

## Anti-patterns
- Don't report three-decimal precision on a back-of-envelope number.
- Don't silently drop outliers — call them out.
- Don't confuse correlation with cause. If your person needs causality, say what evidence they'd need to prove it.
