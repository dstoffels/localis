# Developer Guide

## resolve-subdivisions (Claude Skill)

`ingest_subdivisions()` builds its subdivision set from GeoNames (`admin1CodesASCII.txt`, `admin2Codes.txt`) and merges in ISO 3166-2 as the source of truth, using fuzzy matching (`ingest/subdivisions/scripts/merge_subdivisions.py`) to pair each ISO subdivision with its GeoNames counterpart. Fuzzy matching alone can't confidently resolve every pair, GeoNames and ISO frequently disagree on transliteration, use different eras' names for the same region, or one side uses a colloquial/local form the other doesn't. Others may not have a Geonames counterpart and are added as new entries. 

Whatever's left unmatched after fuzzy merging is an "orphan". Forcing a low-confidence match would silently corrupt the dataset, so orphans are instead handed off for resolution with real-world geographic knowledge using the resolve-subdivisions skill, which is almost entirely automated.

### Pipeline integration

`ingest/subdivisions/outputs/resolution_map.json` is the single source of truth for every ISO subdivision's resolution, not just the ones that needed human help. It's loaded once into a `ResolutionMap` (`ingest/subdivisions/utils/resolution_map.py`) at the start of `ingest_subdivisions()` and threaded through every stage:

1. `apply_skill_resolved()` (`ingest/subdivisions/scripts/resolve_subdivisions.py`) applies every entry in `resolution_map.skill_resolved` directly, before fuzzy matching ever runs, so a human-verified decision can never lose its target to a fresh auto-merge.
2. `try_merge()` (`ingest/subdivisions/scripts/merge_subdivisions.py`) auto-merges whatever's left and writes the result straight into `resolution_map.auto_merge`: a successful match (with its score margin over threshold) into `resolutions`, an unmatched one into `orphans.no_candidates`/`no_matches`/`ambiguity` depending on why. This recomputes fully on every run; a previously-recorded `audited` entry is only kept if the fresh result still matches it exactly (`ResolutionMap.reconcile()`), otherwise it's evicted and replaced, which is how an algorithm improvement self-corrects a stale decision without any manual cache-invalidation step to forget.
3. `resolution_map.save()` persists the whole file at the end of the run, regardless of whether orphans remain, the pipeline runs to completion including cities either way. CI checks orphan state as a fact after the run (`ingest/subdivisions/scripts/check_orphans.py`, exposed as `poetry run check-orphans`), rather than relying on an exit code.

### Resolving Orphans

The skill (`.claude/skills/resolve-subdivisions/SKILL.md`) is a Claude Code skill backed by a local MCP server (`.claude/skills/resolve-subdivisions/scripts/server.py`, can be launched manually via `poetry run python ...`). It drains `resolution_map.json`'s `auto_merge.orphans` lists one entry at a time.

**Tools**

- **`next()`**: Returns the next orphan and a batch of its GeoNames candidates of the same country, ranked by fuzzy score (`rapidfuzz` against every name/alias combo). Geonames candidates are paginated into batches. The first batch is a "top tier" slice (~10% of the pool, ~75% of matches are found in this batch), subsequent batches are fixed 200-candidate chunks, this keeps a country with thousands of subdivisions from blowing out the tool result payload. Repeated `next()` calls page through the same orphan until its candidates run out. Each session has a 1000-candidate soft cap, forcing a session `/clear` to keep agent context from drifting over a long run.
- **`merge(candidate_geonames_id)`**: Resolves the current orphan into a selected GeoNames candidate by its `geonames_id`.
- **`add()`**: Adds the orphan as its own new entry, for subdivisions that are real but have no GeoNames counterpart to merge into.
- **`review()`**: An escalation valve for unresolvable cases. `review` dumps the orphan and its full candidate list to `review_output.json` for a human to inspect and decide manually. The orphan must be resolved with `merge` or `add` before the session can continue.

Both `merge` and `add` write into `resolution_map.skill_resolved`, remove the orphan from whichever `auto_merge.orphans` bucket it was in, and append a one-line audit entry to `resolution_log.txt`.

**Decision funnel** (`SKILL.md` Steps 1–5): try a high-confidence `merge` against the current candidate batch → if none fit, page to the next batch and repeat → if no candidate ever fits but the orphan is a real, confirmed entity, `add` it → if still uncertain, websearch the orphan → if that still doesn't resolve it, `review()` and defer to human intervention.

### State files

Under `ingest/subdivisions/outputs/`:

| File | Written by | Purpose |
|---|---|---|
| `resolution_map.json` | every pipeline run (`auto_merge`, `bypassed`), skill's `merge`/`add` (`skill_resolved`) | Single source of truth for every ISO subdivision's resolution: auto-merged, skill-resolved, non-administrative bypass, or orphaned, by reason |
| `resolution_log.txt` | `log_decision()` | Append-only, human-readable audit trail of every merge/add decision |
| `review_output.json` | skill's `review()` | One-off dump of an escalated orphan + full candidate list for manual human review |


## Data Sourcing

Countries pull ISO 3166-1 codes and names from Debian's iso-codes project, country metadata from GeoNames' `countryInfo.txt`, and additional aliases from a committed Wikidata snapshot (`wiki_countries.json`) that isn't part of the automated fetch. Subdivisions pull ISO 3166-2 codes and names from the same iso-codes project (`iso_3166-2.json`) and admin boundaries from GeoNames' `admin1CodesASCII.txt` and `admin2Codes.txt`; Ipregistry's `iso3166` repository is used only to enrich aliases with its `localVariant` field, iso-codes' own subdivision data has none, the same supplementary role Wikidata plays for countries. Ipregistry's own upstream sourcing is opaque (its data-generation pipeline lives in a private repo), which is exactly why it's kept out of the authoritative path. Cities pull from GeoNames' `cities500.txt`, GeoNames' own pre-filtered export (population ≥ 500, or a seat of an administrative division regardless of population), so `ingest/cities/scripts/load_cities.py` no longer applies its own feature-code or population filtering on top, GeoNames already made that call, and re-filtering on population would wrongly drop the low/no-population admin seats `cities500` specifically includes on purpose.

Fetching is checksum-aware: nothing gets downloaded unless its remote source has actually changed since the last successful fetch. A domain only ever re-fetches all of its sources together, never a subset, since merging needs the complete raw set on disk rather than whatever piece happened to change. That same check gates the rest of the pipeline too, skipping parsing and merging entirely for a domain with nothing new.

### Automated ingest pipeline (CI)

The monthly refresh described above is implemented in `.github/workflows/ingest.yaml`, which runs end-to-end against a long-lived `ingest` branch, on a monthly cron (`0 6 1 * *`) and on every push to `ingest`.

Each run merges the latest `main` into `ingest`, runs `poetry run ingest`, and stages whatever changed. If `src/localis/data` (the published dataset) changed, it bumps the **patch** version with `poetry version patch` before committing. A data refresh doesn't touch the public API, so minor is reserved for genuine backward-compatible additions; conflating the two would mean a consumer reading `1.4.0 → 1.5.0` couldn't tell "just fresher data" from "there's a new method worth checking out." Freshness is still visible, just through the CHANGELOG's per-release counts rather than the version number itself. Bookkeeping files (the per-domain `*.manifest.json`, `resolution_map.json`, `orphaned_subdivisions.json`) can change independently of the dataset output and still get committed on a run where the dataset itself didn't move. Everything staged is committed and pushed back to `ingest`.

CI then runs `poetry run check-orphans` against whatever `orphaned_subdivisions.json` looks like after this run, and maintains a single, persistent `ingest` → `main` pull request: created as a draft on first use, and on every later run commented with that run's actual diff (`git diff --stat HEAD~1 HEAD -- src/localis/data`), so the PR reads as a log of real changes rather than a bare pointer at commit history. If orphans remain, it comments the `check-orphans` summary and fails the job, visible in the Actions tab. If none remain, it calls `gh pr ready` unconditionally, so a run that clears the last orphan without any other upstream change still surfaces as mergeable.

The failing check is advisory, not what actually blocks the merge. What blocks it is the PR staying in **draft**: GitHub disables the merge button on a draft regardless of any check's state, and this repo's branch protection on `main` only restricts direct pushes, it doesn't require this workflow's check to pass. The maintainer's real signal is draft vs. ready; the failed job and comment exist purely for visibility. Resolving orphans is still a local step: pull `ingest`, run the resolve-subdivisions skill, commit, and push back to `origin/ingest`, which re-triggers this workflow through its push trigger.

One bug this surfaced and fixed in passing: `release.yaml`'s checkout step never fetched tags, so its `git tag | sort --version-sort | tail -n1` always came back empty. The workflow believed no version had ever shipped and re-attempted publishing whatever version was already in `pyproject.toml`, which is what actually broke the most recent release (PyPI rejects re-uploading an already-used filename), not a PyPI API change as it first appeared. Fixed with `fetch-tags: true` on that checkout step, which matters here specifically because a merged `ingest` PR is exactly the kind of push to `main` that would retrigger this failure mode.

## Performance Profile

Snapshot taken after the cities500 switch and the entities/views/stores refactor (254 countries, 51,684 subdivisions, 235,895 cities). These numbers move as the dataset grows through the ingest pipeline; re-measure before relying on them for a release decision. Memory figures are retained RSS deltas (`VmRSS` read from `/proc/self/status` after an explicit `gc.collect()`), not `ru_maxrss` peak; see Memory measurement methodology below for why that distinction matters.

### Search and filter index architecture

Both indexes moved off `list[int]` postings (each id a full boxed Python object, ~36 bytes) onto `array.array("I", ...)` (packed 4-byte unsigned ints), for the same reason in both cases: the cost was in the container, not the data.

The search index also changed format on disk. It used to be one TSV line per trigram, `base64(varint(delta(ids)))`, which requires a serial, byte-at-a-time Python loop to decode, that can't be bulk-loaded regardless of the target container. It's now two files: `search_index.bin.gz` (every trigram's sorted ids, packed as raw uint32, concatenated in one buffer, gzip'd as a whole) and `search_index_offsets.tsv` (`trigram, offset, count`, offset/count in id-count units, plain text since it's small and worth keeping git-diffable). Loading decompresses and `array.frombytes()`s the entire blob in one bulk call, then slices per-trigram arrays out of that single decoded array using the offsets table, decode once, slice many, rather than decoding per trigram.

The filter index's fix didn't need a format change, just the container: `FilterIndex.load()` builds its reverse index (`value -> ids`) entirely in memory from per-entity rows already on disk, there was never a variable-length encoding to redesign, so swapping the `defaultdict(list)` factory for `defaultdict(lambda: array("I"))` was the whole change.

### Subdivision hashid

`SubdivisionModel.hashid` is an MD5-derived id used only during ingestion (merging ISO and GeoNames records, and supporting the resolve-subdivisions skill). It used to be computed in `__post_init__`, which runs on every construction, including the normal runtime `_cache` load, where nothing ever reads `hashid`, it's discarded once a subdivision has been merged. `set_hashid()` is now an explicit method, called only at the two ingestion sites that actually need it (`ingest/subdivisions/scripts/geonames_subdivisions.py`, `ingest/subdivisions/scripts/iso_subdivisions.py`); `SubdivisionModel.from_row()`, the runtime path, never calls it. Subdivisions' dataset load dropped from 289.5ms to 98.7ms (−66%) as a result.

### Memory measurement methodology

Earlier benchmarks in this document used `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`, the process's historical peak resident memory, which only ever increases and never reflects memory freed later in the same process. That overstates any component whose loading path allocates a large transient buffer it doesn't keep: `SearchIndex.load()` decompresses its entire gzip blob into one big `array("I")` before slicing per-trigram arrays out of it (a copy, not a view), so the decompression peak gets permanently recorded by `ru_maxrss` even after that buffer is freed and unmapped moments later. Re-measuring with actual post-GC retained memory (`VmRSS` after `gc.collect()`) showed cities' search index really retains about a third of its previously documented figure (33.5MB vs. 96.8MB), while cache and filter index numbers, which don't have this transient-buffer pattern, held up closely under both methodologies. All numbers below use the retained methodology.

### Shipped data size

`src/localis/data/` is 54MB total (down from 98MB after the cities500 switch), almost entirely cities:

| Domain | Size | Share |
|---|---|---|
| Countries | 84KB | 0.15% |
| Subdivisions | 8.0MB | 14.8% |
| Cities | 46MB | 85.1% |

Within cities: `cities.tsv` 13MB, `filter_index.tsv` 18MB, `search_index.bin.gz` 13MB, `search_index_offsets.tsv` 236KB, `lookup_index_int.tsv` 3.3MB.

### Memory footprint

| Registry (`force_cache()`) | Retained memory |
|---|---|
| countries | 892KB |
| subdivisions | 44.6MB |
| cities | 150.1MB |
| **total, all three fully cached** | **195.6MB** |

Cities' 150.1MB breaks down further by structure:

| Cities component | Retained memory | Build time |
|---|---|---|
| `_cache` (235,895 views) | 59.9MB | 395ms |
| `_lookup_index` | 4KB | 59ms |
| `_filter_index` | 56.7MB | 543ms |
| `_search_index` | 33.5MB | 144ms |

**Total load time** (all three registries, `_cache` plus every index) is ~1.4s.

### Population floor

`CityRegistry.set_population_threshold(n)` narrows the cache and all three indexes to cities with population >= n, implemented via two predicate protocols in `localis/utils/data.py`: `CacheFilterPredicate` (`row -> bool`, evaluated inline as `CityView.load()` parses each TSV row, since population is only known once that row is parsed) and `IndexFilterPredicate` (`(id, allowed_ids) -> bool`, the shared membership check `Registry._is_id_allowed()` implements for `FilterIndex`/`SearchIndex`/`LookupIndex`, none of which have population data of their own and can only ever ask "is this id still allowed"). `CityRegistry.build_cache()` derives `self._allowed_ids` as a byproduct of the `CityView.load()` pass it already has to do; `Registry._lookup_index`/`_filter_index`/`_search_index` force `self._cache` before building, guaranteeing `_allowed_ids` reflects the current threshold, since none of the three indexes have any real use without the cache regardless of population filtering.

Ids stay stable across thresholds. `Store.id_to_idx` (an `array.array("i")` sized to the full unfiltered id space, `-1` for an excluded id) decouples a View's physical position in its Store from its public `id`, so `View._idx` resolves through this array instead of assuming `id - 1`. That lets `CityStore` skip allocating rows for excluded cities entirely, a real memory saving rather than just fewer View wrapper objects, without ever renumbering an id a caller might already be holding.

At a 15,000 threshold (the tier geonamescache ships as a separate bundled dataset), cities drops from 235,895 to 34,167 and retained memory drops from 150.1MB to 31.5MB.
