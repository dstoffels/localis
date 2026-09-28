# Developer Guide

## resolve-subdivisions (Claude Skill)

`ingest_subdivisions()` builds its subdivision set from GeoNames (`admin1CodesASCII.txt`, `admin2Codes.txt`) and merges in ISO 3166-2 as the source of truth, using fuzzy matching (`data/subdivisions/scripts/merge_subdivisions.py`) to pair each ISO subdivision with its GeoNames counterpart. Fuzzy matching alone can't confidently resolve every pair, GeoNames and ISO frequently disagree on transliteration, use different eras' names for the same region, or one side uses a colloquial/local form the other doesn't. Others may not have a Geonames counterpart and are added as new entries. 

Whatever's left unmatched after fuzzy merging is an "orphan". Forcing a low-confidence match would silently corrupt the dataset, so orphans are instead handed off for resolution with real-world geographic knowledge using the resolve-subdivisions skill, which is almost entirely automated.

### Pipeline integration

`resolve_unmerged_subs()` (`data/subdivisions/scripts/resolve_subdivisions.py`) is the seam between fuzzy matching and manual resolution:

1. It first re-applies any previously recorded decisions from `resolution_map.json` (see below) to the unmerged list, this is what makes resolutions durable across ingest runs.
2. Otherwise, remaining orphans are dumped to `orphaned_subdivisions.json` keyed by ISO code via `dump_orphans()`, and the pipeline runs to completion regardless, including cities. It used to hard-stop with `sys.exit(10)` the moment an orphan was found, but that made a run all-or-nothing: a single unresolved orphan meant nothing else from that run, including subdivisions that resolved cleanly, ever landed. Now any remaining orphans are just a known, tracked gap, and everything else still merges. CI treats orphan state as a fact to check after the run, reading `orphaned_subdivisions.json` directly (`data/subdivisions/scripts/check_orphans.py`, exposed as `poetry run check-orphans`), rather than relying on an exit code.

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

### Automated ingest pipeline (CI)

The monthly refresh described above is implemented in `.github/workflows/ingest.yaml`, which runs end-to-end against a long-lived `ingest` branch, on a monthly cron (`0 6 1 * *`) and on every push to `ingest`.

Each run merges the latest `main` into `ingest`, runs `poetry run ingest`, and stages whatever changed. If `src/localis/data` (the published dataset) changed, it bumps the **patch** version with `poetry version patch` before committing. A data refresh doesn't touch the public API, so minor is reserved for genuine backward-compatible additions; conflating the two would mean a consumer reading `1.4.0 → 1.5.0` couldn't tell "just fresher data" from "there's a new method worth checking out." Freshness is still visible, just through the CHANGELOG's per-release counts rather than the version number itself. Bookkeeping files (the per-domain `*.manifest.json`, `resolution_map.json`, `orphaned_subdivisions.json`) can change independently of the dataset output and still get committed on a run where the dataset itself didn't move. Everything staged is committed and pushed back to `ingest`.

CI then runs `poetry run check-orphans` against whatever `orphaned_subdivisions.json` looks like after this run, and maintains a single, persistent `ingest` → `main` pull request: created as a draft on first use, and on every later run commented with that run's actual diff (`git diff --stat HEAD~1 HEAD -- src/localis/data`), so the PR reads as a log of real changes rather than a bare pointer at commit history. If orphans remain, it comments the `check-orphans` summary and fails the job, visible in the Actions tab. If none remain, it calls `gh pr ready` unconditionally, so a run that clears the last orphan without any other upstream change still surfaces as mergeable.

The failing check is advisory, not what actually blocks the merge. What blocks it is the PR staying in **draft**: GitHub disables the merge button on a draft regardless of any check's state, and this repo's branch protection on `main` only restricts direct pushes, it doesn't require this workflow's check to pass. The maintainer's real signal is draft vs. ready; the failed job and comment exist purely for visibility. Resolving orphans is still a local step: pull `ingest`, run the resolve-subdivisions skill, commit, and push back to `origin/ingest`, which re-triggers this workflow through its push trigger.

One bug this surfaced and fixed in passing: `release.yaml`'s checkout step never fetched tags, so its `git tag | sort --version-sort | tail -n1` always came back empty. The workflow believed no version had ever shipped and re-attempted publishing whatever version was already in `pyproject.toml`, which is what actually broke the most recent release (PyPI rejects re-uploading an already-used filename), not a PyPI API change as it first appeared. Fixed with `fetch-tags: true` on that checkout step, which matters here specifically because a merged `ingest` PR is exactly the kind of push to `main` that would retrigger this failure mode.

## Performance Profile

Snapshot as of v1.1.1 (254 countries, 51,684 subdivisions, 472,613 cities). These numbers move as the dataset grows through the ingest pipeline; re-measure before relying on them for a release decision. Memory figures are RSS deltas measured by calling `force_cache()` on each registry in turn from a fresh interpreter.

### Shipped data size

`src/localis/data/` is 95MB total, almost entirely cities:

| Domain | Size | Share |
|---|---|---|
| Countries | 68KB | 0.07% |
| Subdivisions | 7.4MB | 7.8% |
| Cities | 88MB | 92.6% |

Within cities, the four files break down as: `cities.tsv` 26MB, `cities_filter_index.tsv` 35MB, `cities_search_index.tsv` 24MB, `cities_lookup_index.tsv` 3.6MB.

### Memory footprint

| Registry (`force_cache()`) | RSS delta |
|---|---|
| import baseline | 37MB |
| countries | +0.4MB |
| subdivisions | +93MB |
| cities | +995MB |
| **total, all three fully cached** | **1134MB** |

Cities' 995MB breaks down further by structure:

| Cities component | RSS delta |
|---|---|
| `_cache` (472,613 models) | 180MB |
| `_lookup_index` | 61MB |
| `_filter_index` | 109MB |
| `_search_index` | 645MB |

The search (trigram) index is 62% of cities' footprint and 57% of the package's total peak memory, despite being the second-smallest file on disk (24MB). The inflation comes from decoding the compact on-disk posting format (base64 + varint + delta encoded) into `dict[str, list[int]]`: each id ends up as a full boxed `int` object referenced by a list, roughly 36 bytes per id, instead of the 4 bytes a packed representation (e.g. `array.array("I", ...)`) would cost. This is a representation cost, not a data-volume cost: it doesn't shrink by reducing the dataset, only by changing how decoded postings are stored in memory.

### City population distribution

`cities.tsv` population field, all 472,613 rows, sorted:

| Threshold | Cities remaining | Share |
|---|---|---|
| population > 0 (current) | 472,613 | 100% |
| population > 100 | 304,916 | 64.5% |
| population > 500 | 186,310 | 39.4% |
| population > 1,000 | 138,441 | 29.3% |
| population > 5,000 | 63,775 | 13.5% |

Median population across the current dataset is 263. The current ingestion filter (`data/cities/scripts/load_cities.py`) admits any populated-place feature code (PPL, PPLA, PPLA2-5, PPLC, PPLF, PPLL, PPLS, STLMT) with a nonzero population; it does not apply a population floor.
