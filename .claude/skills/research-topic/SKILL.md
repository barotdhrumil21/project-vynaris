---
name: research-topic
description: Conduct focused desk research on a topic using web search + fetch, then produce a structured summary with citations. Use when your person needs context or market scan on something new.
---

# Research a topic

Use this skill when your person asks you to understand a topic, scan a market, or gather outside context.

## Steps

1. **Narrow the question.** If the ask is vague, write a 1-sentence precise version in `private/research-<slug>.md`.
2. **Search broadly, then deeply.** Use `web_search` for the precise question. Pick the 4–6 most promising results.
3. **Fetch and extract.** For each, `web_fetch` and pull the 3–5 facts that matter for the question. Save the URL + notes in the research file.
4. **Synthesize.** Write a short report to `public/research-<slug>.md` with:
   - The question
   - Bottom-line answer (2–3 sentences)
   - 3–5 supporting findings, each with a citation
   - Open questions / what we still don't know
5. **Post to feed.** Call `post_feed` with a 1-line summary and a link to the public report (visibility = team).

## Anti-patterns
- Don't dump raw search snippets; always synthesize.
- Don't claim a finding without a citation. If you can't cite, frame as "my inference".
- Don't produce reports longer than 400 words for a first pass.
