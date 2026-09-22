---
name: resolve-subdivisions
description: Resolves ISO 3166-2 subdivisions that localis's data-ingestion pipeline flagged as orphaned — ones fuzzy-matching couldn't confidently merge with a GeoNames counterpart. Uses real-world geographic knowledge (transliteration variants, historical or colloquial name changes, language variants) to pick the correct match with high confidence, or explicitly escalates genuinely ambiguous cases to a human instead of guessing. Use this whenever data/subdivisions/raw/orphaned_subdivisions.json exists, a subdivisions pipeline run exited with the orphaned-subs exit code, or you're asked to resolve orphaned subdivisions / populate data/subdivisions/raw/resolution_map.json — as the tier between the pipeline's automatic fuzzy-matching and a human running the interactive terminal wizard.
---

# Resolve Subdivisions

## Status

Not yet run against real data.

## Why this exists

`data/subdivisions/raw/orphaned_subdivisions.json` is written by the subdivisions pipeline when it can't auto-resolve every ISO subdivision against its GeoNames counterpart, and the pipeline hard-exits at that point — `ingest_cities()` never runs on an incomplete subdivision map. This skill's job is to resolve as many of those orphans as possible using real-world knowledge fuzzy-matching couldn't apply, before a human has to.

## Workflow

You are the orchestrator, dispatching bounded subagents to do the actual resolution work, not looping through hundreds of entries yourself in this conversation. Holding all of them in one context at once is exactly what this design avoids.

1. **Check there's something to do.** Run:
   ```
   poetry run python .claude/skills/resolve-subdivisions/scripts/api.py next
   ```
   If it prints `null`, nothing's orphaned right now — say so rather than inventing work.

2. **Dispatch a subagent for a bounded batch.** Use the Agent tool. Use this exact prompt every time, verbatim — do not paraphrase or re-explain the task yourself, that's the one thing to avoid here:
   ```
   Run .claude/skills/resolve-subdivisions/references/worker.md.
   ```

3. **Dispatch another subagent, and repeat, until `next` returns `null`.** One batch at a time, never concurrently (see Guardrails).

## Guardrails

- Dispatch batches sequentially, never concurrently — neither `orphaned_subdivisions.json` nor `resolution_map.json` has any locking, so two subagents writing at the same time could silently clobber each other's decisions.
- After this skill runs, the pipeline needs to actually be re-run to pick up the new `resolution_map.json` entries and (assuming nothing's left orphaned) finish subdivisions and proceed to cities. This skill doesn't re-run the pipeline itself.
