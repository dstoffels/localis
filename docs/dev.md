# Developer Guide

## resolve-subdivisions (Claude Skill)

`ingest_subdivisions()` builds its subdivision set from GeoNames (`admin1CodesASCII.txt`, `admin2Codes.txt`) and merges in ISO 3166-2 as the source of truth, using fuzzy matching (`data/subdivisions/scripts/merge_subdivisions.py`) to pair each ISO subdivision with its GeoNames counterpart. Fuzzy matching alone can't confidently resolve every pair, GeoNames and ISO frequently disagree on transliteration, use different eras' names for the same region, or one side uses a colloquial/local form the other doesn't. Others may not have a Geonames counterpart and are added as new entries. 

Whatever's left unmatched after fuzzy merging is an "orphan". Forcing a low-confidence match would silently corrupt the dataset, so orphans are instead handed off for resolution with real-world geographic knowledge using the resolve-subdivisions skill, which is almost entirely automated.

### Pipeline integration

`resolve_unmerged_subs()` (`data/subdivisions/scripts/resolve_subdivisions.py`) is the seam between fuzzy matching and manual resolution:

1. It first re-applies any previously recorded decisions from `resolution_map.json` (see below) to the unmerged list, this is what makes resolutions durable across ingest runs.
2. Otherwise, remaining orphans are dumped to `orphaned_subdivisions.json` keyed by ISO code, and the process exits with code `10` (`ORPHANED_SUBS_EXIT_CODE`) to hard-stop the pipeline, a partial subdivision merge shouldn't silently continue downstream into cities.

### The resolve-subdivisions skill & MCP server

The skill (`.claude/skills/resolve-subdivisions/SKILL.md`) is a Claude Code skill backed by a local MCP server (`.claude/skills/resolve-subdivisions/scripts/server.py`, can be launched manually via `poetry run python ...`). It drains `orphaned_subdivisions.json` one entry at a time.

**Tools**

- **`next()`**: Returns the next orphan from `orphaned_subdivisions.json` and a batch of its GeoNames candidates of the same country, ranked by fuzzy score (`rapidfuzz` against every name/alias combo). Geonames candidates are paginated into batches. The first batch is a "top tier" slice (~10% of the pool, ~75% of matches are found in this batch), subsequent batches are fixed 200-candidate chunks, this keeps a country with thousands of subdivisions from blowing out the tool result payload. Repeated `next()` calls page through the same orphan until its candidates run out. Each session has a 1000-candidate soft cap, forcing a session `/clear` to keep agent context from drifting over a long run.
- **`merge(candidate_hashid, aliases=[])`**: Merges the current orphan into a GeoNames candidate by hashid. 
- **`add(aliases=[])`**: Adds the orphan as its own new entry, for subdivisions that are real but have no GeoNames counterpart to merge into.
- **`review()`**: An escalation valve for genuinely ambiguous cases. `review` dumps the orphan and its full, unpaginated candidate list to `review_output.json` for a human to inspect and decide manually. The orphan must be resolved with `merge` or `add` before the session can continue.

Both `merge` and `add` write to `resolution_map.json`  remove the orphan from `orphaned_subdivisions.json`, and append a one-line audit entry to `resolution_log.txt`.

**Decision funnel** (`SKILL.md` Steps 1–5): try a high-confidence `merge` against the current candidate batch → if none fit, page to the next batch and repeat → if no candidate ever fits but the orphan is a real, confirmed entity, `add` it → if still uncertain, websearch the orphan → if that still doesn't resolve it, `review()` and defer to human intervention.

### State files

All under `data/subdivisions/raw/` (gitignored except these, per `.gitignore`'s whitelist):

| File | Written by | Purpose |
|---|---|---|
| `orphaned_subdivisions.json` | `resolve_subdivisions.py` (produced), skill / `pop_orphan()` (drained) | Queue of unresolved ISO subdivisions, keyed by ISO code |
| `resolution_map.json` | skill's `merge`/`add` | Durable decision cache, keyed by ISO code; re-applied automatically on every ingest run |
| `resolution_log.txt` | `log_decision()` | Append-only, human-readable audit trail of every merge/add decision |
| `review_output.json` | skill's `review()` | One-off dump of an escalated orphan + full candidate list for manual human review |


## Data Sourcing

Countries pull ISO 3166-1 codes and names from Debian's iso-codes project, country metadata from GeoNames' `countryInfo.txt`, and additional aliases from a committed Wikidata snapshot (`wiki_countries.json`) that isn't part of the automated fetch. Subdivisions pull ISO 3166-2 codes from Ipregistry's `iso3166` repository and admin boundaries from GeoNames' `admin1CodesASCII.txt` and `admin2Codes.txt`. Cities pull from GeoNames' `allCountries.txt`, filtered down to populated places by feature code (PPL, PPLA, PPLA2, PPLA3, PPLA4, PPLA5, PPLC, PPLF, PPLL, PPLS, STLMT).

Fetching is checksum-aware: nothing gets downloaded unless its remote source has actually changed since the last successful fetch. A domain only ever re-fetches all of its sources together, never a subset, since merging needs the complete raw set on disk rather than whatever piece happened to change. That same check gates the rest of the pipeline too, skipping parsing and merging entirely for a domain with nothing new.

### Automated refresh (planned)

Source data will be refreshed on a monthly schedule via a CI job that re-fetches from GeoNames and the ISO sources, skipping anything that hasn't changed since the last run. When the new data merges cleanly it opens a pull request with the updated dataset; anything it can't resolve automatically is flagged for manual review instead.
