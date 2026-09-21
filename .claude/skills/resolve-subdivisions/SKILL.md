---
name: resolve-subdivisions
description: Resolves ISO 3166-2 subdivisions that localis's data-ingestion pipeline couldn't confidently auto-merge with a GeoNames counterpart via fuzzy string matching. Uses real-world geographic knowledge (transliteration variants, historical or colloquial name changes, language variants) to pick the correct match with high confidence, or explicitly flags genuinely ambiguous cases for a human to resolve. Use this whenever asked to resolve orphaned/unmatched subdivisions, populate or update data/subdivisions/raw/resolution_map.json, or run the "tier 2, model-level" resolution step of the subdivisions pipeline — as an alternative to manually running the interactive terminal wizard in resolve_subdivisions.py.
---

# Resolve Subdivisions

## Status

Draft — written up for review and editing, not yet run end-to-end against real data. The two bundled scripts below have not been executed; check them over before trusting their output. No files under `data/subdivisions/scripts/` have been touched — this skill only reads from the existing pipeline and writes to `data/subdivisions/raw/resolution_map.json`.

## Why this exists

`try_merge()` in [data/subdivisions/scripts/merge_subdivisions.py](../../../data/subdivisions/scripts/merge_subdivisions.py) auto-merges most ISO subdivisions to their GeoNames counterpart using `rapidfuzz` token-set string similarity. That catches the easy cases but has no real-world knowledge — it can't tell that "Cherkashchyna" and "Cherkasy" name the same Ukrainian oblast, because that's a fact about the world, not a string-similarity fact. Around ~700 subdivisions fail the fuzzy-match threshold today and fall through to `_resolve_interactively()` in [resolve_subdivisions.py](../../../data/subdivisions/scripts/resolve_subdivisions.py), which makes a human sit through a terminal wizard for every single one.

This skill is the middle tier: **code auto-merges what it can → the model resolves what it can, with its own knowledge, at its own authority → only genuine leftovers go to a human.** The model's decisions are not meant to be rubber-stamped by a human afterward — if you're not confident, that specific case should be escalated instead of decided, not decided-then-checked. A wrong merge here silently corrupts a real subdivision record with no error thrown anywhere downstream, so escalating an uncertain case is always the right call over guessing.

## Open design question

This draft assumes **batch processing**: dump every unresolved subdivision + its candidates up front, resolve the whole batch in one pass, then write all decisions back at once. The alternative — reusing `_resolve_interactively()`'s per-item loop but swapping the `input()` call for the model's own choice — was considered and rejected for this draft because it would mean threading a non-interactive decision path through code that currently exists purely to drive a terminal UI, and would process one subdivision per exchange for ~700 of them for no real accuracy benefit. Batch processing also leaves `_resolve_interactively()` completely untouched, so it's still there, unmodified, as the actual tier-3 human fallback. If you disagree, this is the part of the design to revisit.

## Workflow

1. **Dump the unresolved set.** Run:
   ```
   poetry run python .claude/skills/resolve-subdivisions/scripts/dump_unmatched.py --out unmatched_subdivisions.json
   ```
   This replays the pipeline's own logic (`load_countries` → `map_geonames_subdivisions` → `load_iso_subs` → `try_merge`) against whatever source files are already sitting in `data/subdivisions/raw/`, and writes out every ISO subdivision that failed fuzzy-matching *and* has no existing entry in `resolution_map.json` (i.e. genuinely still needs a decision), each with its name/aliases and the same numbered candidate list a human would see in the interactive wizard. It does not fetch fresh source data — if you want this to reflect the latest upstream ISO/GeoNames data, run the pipeline's own fetch step first.

2. **Resolve each entry using real-world knowledge, not string similarity.** String similarity already had its shot — it's why this entry is in the unresolved set at all. For each subdivision in `unmatched_subdivisions.json`, decide one of three things:
   - **`merge`** — you recognize, with real confidence, that this ISO subdivision and one specific numbered candidate are the same place (different transliteration, an old vs. current name, a local vs. official form, etc.). Record that candidate's `hashid`, plus any name variants worth keeping as aliases.
   - **`add`** — there's genuinely no matching GeoNames candidate (e.g. a subdivision GeoNames doesn't track). Add it standalone.
   - **`escalate`** — you're not genuinely confident: two candidates are both plausible, the naming is disputed or politically contested, or there isn't enough information to tell. Say why in one line. Do not pick the "least bad" option just to avoid escalating.

   Write your decisions to a JSON file in this shape:
   ```json
   [
     {"iso_code": "UA-71", "decision": "merge", "hashid": 123456789012345678, "names": ["Cherkashchyna"]},
     {"iso_code": "XX-99", "decision": "add", "names": []},
     {"iso_code": "YY-01", "decision": "escalate", "reason": "two equally plausible candidates; can't tell which is current"}
   ]
   ```
   Only include a `hashid` that actually came from that entry's own candidate list — never invent one.

3. **Apply the decisions.** Run:
   ```
   poetry run python .claude/skills/resolve-subdivisions/scripts/apply_resolutions.py decisions.json
   ```
   This merges `merge`/`add` decisions into `data/subdivisions/raw/resolution_map.json` in the exact shape `_apply_cached_resolution()` already expects (so they replay automatically on the next real pipeline run, same as any manually-resolved entry), and writes everything marked `escalate` to a sibling `escalated_to_human.json` report instead of touching `resolution_map.json` for those.

4. **Report back to whoever asked for this.** State how many were resolved automatically vs. escalated, and point at `escalated_to_human.json`. Escalated entries still need a human to run:
   ```
   poetry run python -m data.subdivisions.ingest_subdivisions --interactive
   ```
   to resolve them the existing way.

## Guardrails

- Never fabricate a `hashid` — it must be one of the numbers/hashids actually listed for that specific entry's candidates.
- Re-running this skill is safe: `apply_resolutions.py` merges into the existing `resolution_map.json` rather than overwriting it, so previously-resolved entries are untouched.
- This skill decides *which* GeoNames record (if any) an ISO subdivision corresponds to — it does not construct the final merged subdivision record itself. The actual field merging (name/alias/admin_level reconciliation) still happens inside the live pipeline's `resolve_unmatched_subs()` the next time it runs with this updated `resolution_map.json`.
- If `dump_unmatched.py` reports zero unresolved entries, there's nothing for this skill to do — say so rather than inventing work.
