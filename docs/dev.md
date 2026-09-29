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

Snapshot taken after the search-index and filter-index memory rework and the subdivision `hashid` fix (254 countries, 51,684 subdivisions, 472,613 cities). These numbers move as the dataset grows through the ingest pipeline; re-measure before relying on them for a release decision. Memory figures are RSS deltas measured by calling `force_cache()` on each registry in turn from a fresh interpreter.

### Search and filter index architecture

Both indexes moved off `list[int]` postings (each id a full boxed Python object, ~36 bytes) onto `array.array("I", ...)` (packed 4-byte unsigned ints), for the same reason in both cases: the cost was in the container, not the data.

The search index also changed format on disk. It used to be one TSV line per trigram, `base64(varint(delta(ids)))`, which requires a serial, byte-at-a-time Python loop to decode, that can't be bulk-loaded regardless of the target container. It's now two files: `search_index.bin.gz` (every trigram's sorted ids, packed as raw uint32, concatenated in one buffer, gzip'd as a whole) and `search_index_offsets.tsv` (`trigram, offset, count`, offset/count in id-count units, plain text since it's small and worth keeping git-diffable). Loading decompresses and `array.frombytes()`s the entire blob in one bulk call, then slices per-trigram arrays out of that single decoded array using the offsets table, decode once, slice many, rather than decoding per trigram.

The filter index's fix didn't need a format change, just the container: `FilterIndex.load()` builds its reverse index (`value -> ids`) entirely in memory from per-entity rows already on disk, there was never a variable-length encoding to redesign, so swapping the `defaultdict(list)` factory for `defaultdict(lambda: array("I"))` was the whole change.

### Subdivision hashid

`SubdivisionModel.hashid` is an MD5-derived id used only during ingestion (merging ISO and GeoNames records, and supporting the resolve-subdivisions skill). It used to be computed in `__post_init__`, which runs on every construction, including the normal runtime `_cache` load, where nothing ever reads `hashid`, it's discarded once a subdivision has been merged. `set_hashid()` is now an explicit method, called only at the two ingestion sites that actually need it (`data/subdivisions/scripts/geonames_subdivisions.py`, `data/subdivisions/scripts/iso_subdivisions.py`); `SubdivisionModel.from_row()`, the runtime path, never calls it. Subdivisions' dataset load dropped from 289.5ms to 98.7ms (−66%) as a result.

### Shipped data size

`src/localis/data/` is 98MB total, almost entirely cities:

| Domain | Size | Share |
|---|---|---|
| Countries | 72KB | 0.07% |
| Subdivisions | 7.8MB | 8.0% |
| Cities | 91MB | 92.9% |

Within cities: `cities.tsv` 26MB, `filter_index.tsv` 35MB, `search_index.bin.gz` 26MB, `search_index_offsets.tsv` 268KB, `lookup_index.tsv` 3.6MB. The search index's disk footprint grew slightly (24MB → 26.3MB combined) since gzip'd raw fixed-width ids don't compress quite as tightly as the old adaptive varint encoding, an intentional, small trade for the load-time win below.

### Memory footprint

| Registry (`force_cache()`) | RSS delta |
|---|---|
| import baseline | 37MB |
| countries | +1.0MB |
| subdivisions | +42MB |
| cities | +498MB |
| **total, all three fully cached** | **587MB** |

Down from 1134MB before this rework, a 48% reduction overall. Cities' 498MB breaks down further by structure:

| Cities component | RSS delta | Build time |
|---|---|---|
| `_cache` (472,613 models) | 180MB | 0.76s |
| `_lookup_index` | 61MB | 0.14s |
| `_filter_index` | 78MB | 1.06s |
| `_search_index` | 195MB | 0.30s |

`_search_index` dropped from 645MB to 195MB (−70%) and from 1.57s to 0.30s to build (5.2x faster), the single biggest change in this rework. `_filter_index` dropped from 109MB to 78MB (−29%) at effectively unchanged build time, the `array.array` swap only ever targeted memory, not load speed, there was no encoding overhead to remove on that side.

The remaining 195MB in `_search_index` is somewhat inflated by how `load()` currently builds it: one full temporary array is decoded via `frombytes()`, then sliced per trigram, and each slice is a copy, not a view, so the id data briefly exists twice before the temporary array is garbage collected. Using `memoryview` or writing directly into per-trigram arrays instead of slicing a shared one could shave further off this specific number; not done here, since the 70% reduction already achieved doesn't need it to be worth shipping.

**Total load time** (all three registries, `_cache` plus every index) is now ~2.8s, down from ~4.3s. Subdivisions' combined load (dataset plus all three indexes) dropped from ~440ms to ~240ms: ~350ms to ~153ms of that was the index-build improvement described above, and the dataset load itself dropped a further ~191ms (289.5ms → 98.7ms) once `hashid` stopped being computed at runtime.

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
