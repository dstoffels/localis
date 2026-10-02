# Developer Guide

## resolve-subdivisions (Claude Skill)

`ingest_subdivisions()` builds its subdivision set from GeoNames (`admin1CodesASCII.txt`, `admin2Codes.txt`) and merges in ISO 3166-2 as the source of truth, using fuzzy matching (`ingest/subdivisions/scripts/automerge/`) to pair each ISO subdivision with its GeoNames counterpart. Fuzzy matching alone can't confidently resolve every pair, GeoNames and ISO frequently disagree on transliteration, use different eras' names for the same region, or one side uses a colloquial/local form the other doesn't. Others may not have a Geonames counterpart and are added as new entries. 

Whatever's left unmatched after fuzzy merging is an "orphan". Forcing a low-confidence match would silently corrupt the dataset, so orphans are instead handed off for resolution with real-world geographic knowledge using the resolve-subdivisions skill, which is almost entirely automated.

### Pipeline integration

`ingest/subdivisions/outputs/resolution_map.json` is the single source of truth for every ISO subdivision's resolution, not just the ones that needed human help. It's loaded once into a `ResolutionMap` (`ingest/subdivisions/utils/resolution_map.py`) at the start of `ingest_subdivisions()` and threaded through every stage:

1. `apply_skill_decisions()` (`ingest/subdivisions/scripts/resolve_subdivisions.py`) applies every entry in `resolution_map.skill_decisions` directly, before fuzzy matching ever runs, so a human-verified decision can never lose its target to a fresh auto-merge.
2. `try_merge()` (`ingest/subdivisions/scripts/automerge/try_merge.py`) auto-merges whatever's left and writes the result straight into `resolution_map.automerge`: a successful match (with its score margin over threshold) into `resolutions`, an unmatched one into `orphans.no_candidates`/`no_matches`/`ambiguity` depending on why, and a winning match less than `MARGIN_FLOOR` (5) points over its threshold into `orphans.low_margin` with its candidate, for the skill to confirm or reject. ISO subdivisions of a country with no GeoNames subdivisions at all are added as-is and listed in `geonames_absent` instead of orphaned, since there is nothing for the skill to decide. This recomputes fully on every run; a previously-recorded `audited` entry is only kept if the fresh result still matches it exactly (`ResolutionMap.reconcile()`), otherwise it's evicted and replaced, which is how an algorithm improvement self-corrects a stale decision without any manual cache-invalidation step to forget.
3. `resolution_map.save()` persists the whole file immediately after merging, regardless of whether orphans remain, so the skill always has the current state to work from. Then a hard gate: if any orphans remain in any of the six buckets (the four from `try_merge()`; `wikidata_conflict`, from `flag_wikidata_conflicts()`, which re-sends any skill decision that disagrees with a valid Wikidata mapping it didn't record in `wikidata_seen`; and `grouping_twin`, from `flag_grouping_twin_merges()`, which re-sends an automerge result that went into a non-administrative grouping's GeoNames twin because `apply_non_administrative()` couldn't identify the twin before automerge ran), `ingest_subdivisions()` logs the exact counts and calls `sys.exit(10)` before `dump()` or the handoff to `ingest_cities()` ever runs, refusing to ship an incomplete dataset. The gate runs only after merging, on freshly recomputed orphans, never at the start of a run: a rerun is how a pipeline fix reaches orphans left by an earlier run, and skill decisions already made persist in `skill_decisions` across reruns. A clean run (no orphans) proceeds to dump subdivisions, regenerate `docs/unmerged_subdivisions.md`, and hand its geocode map to cities ingestion.

### Resolving Orphans

The skill (`.claude/skills/resolve-subdivisions/SKILL.md`) is a Claude Code skill backed by a local MCP server (`.claude/skills/resolve-subdivisions/scripts/server.py`, can be launched manually via `poetry run python ...`). It drains `resolution_map.json`'s `automerge.orphans` lists one entry at a time.

Run the skill with Opus 5.5 or a stronger model. Earlier runs with Sonnet 5 produced enough wrong merges and unjustified adds to leave dirty data and duplicate records, while an audit of 107 Opus 5.5 decisions found none.

**Tools**

- **`next()`**: Returns the next orphan and a batch of candidates drawn from every GeoNames subdivision in its country, regardless of level, since ISO and GeoNames can file the same place at different levels. Candidates are ranked by the same `score_candidates()`/type-family-filtered scoring auto-merge uses, with same-level candidates first on ties, and paginated: a "top tier" first batch (~10% of the pool, ~75% of matches are found here), then fixed 200-candidate chunks. Records already claimed by another ISO code are included but marked `CLAIMED BY <iso_code>`, so a wrong earlier claim is visible; `merge` rejects them. Records the type-family rule would disqualify are included too (`score_candidates(..., include_type_disqualified=True)`), marked as a type mismatch, since that rule misfires on cases like city-states. `ambiguity` and `low_margin` orphans get the specific GeoNames records `try_merge` flagged as their first batch (contested targets, or the near-threshold pick), and fall through to the full pool, those records excluded, only if the agent rejects them. Candidates come back as a list ordered best first, not an ID-keyed dict, since serialization sorts dict keys and loses the ranking. Repeated `next()` calls page through the same orphan until its candidates run out. Each session has a context budget of about 150k estimated tokens (`TOKEN_BUDGET` in `server.py`): the server counts its own output and adds fixed allowances per orphan and per web search, since it can't see the agent's reasoning or search results. Once the budget is reached, the next `next()` call between orphans asks the user to `/clear`. The budget exists mainly for cost, since every call resends the whole context.
- **`merge(candidate_geonames_id)`**: Resolves the current orphan into a selected, unclaimed GeoNames candidate by its `geonames_id`.
- **`add(reason)`**: Adds the orphan as its own new entry, for subdivisions that are real but have no GeoNames counterpart. `reason` must say concretely why GeoNames lacks the place.
- **`review(reason)`**: An escalation valve for unresolvable cases. The agent reports its findings to the user in the session and asks for the decision, then the reason, with `AskUserQuestion`, and the server holds `reason` until the user's decision comes back through `merge` or `add`, which stores it as the decision's `escalation`. The candidate list isn't persisted, since it can be regenerated from the data. The orphan must be resolved with `merge` or `add` before the session can continue.

Both `merge` and `add` write a `SkillDecision` into `resolution_map.skill_decisions` (`id`, `reason`, `decided_by`, which is `"human"` when the orphan was escalated with `review` first and `"agent"` otherwise, and `escalation`, the agent's findings for a human decision) and remove the orphan from whichever `automerge.orphans` bucket it was in. Both require a `reason`: for `merge`, one sentence on why the candidate is the same place.

**Decision funnel** (`SKILL.md` Steps 1–4): try a high-confidence `merge` against the current candidate batch → if none fit, page to the next batch and repeat → once `next()` returns no candidates at all, websearch the orphan first, always, before deciding anything (merge if the search reveals a confident match, `add` if it confirms the orphan is real but has no GeoNames counterpart) → if the search still doesn't resolve it, `review()` and defer to human intervention. The old path that allowed a self-certified `add` without searching first was removed after it produced reckless, unverified adds; websearch is now mandatory, not a last resort.

### State files

Under `ingest/subdivisions/outputs/`:

| File | Written by | Purpose |
|---|---|---|
| `resolution_map.json` | every pipeline run (`automerge`, `bypassed`), skill's `merge`/`add` (`skill_decisions`) | Single source of truth for every ISO subdivision's resolution: auto-merged, skill-resolved, non-administrative bypass, or orphaned, by reason |


## Data Sourcing

Countries pull ISO 3166-1 codes and names from Debian's iso-codes project, country metadata from GeoNames' `countryInfo.txt`, and additional aliases from a committed Wikidata snapshot (`wiki_countries.json`) that isn't part of the automated fetch. Subdivisions pull ISO 3166-2 codes and names from the same iso-codes project (`iso_3166-2.json`) and admin boundaries from GeoNames' `admin1CodesASCII.txt` and `admin2Codes.txt`, with aliases from GeoNames' alternate names. Cities pull from GeoNames' `cities500.txt`, GeoNames' own pre-filtered export (population ≥ 500, or a seat of an administrative division regardless of population), so `ingest/cities/scripts/load_cities.py` no longer applies its own feature-code or population filtering on top, GeoNames already made that call, and re-filtering on population would wrongly drop the low/no-population admin seats `cities500` specifically includes on purpose.

Fetching is checksum-aware: nothing gets downloaded unless its remote source has actually changed since the last successful fetch. A domain only ever re-fetches all of its sources together, never a subset, since merging needs the complete raw set on disk rather than whatever piece happened to change. That same check gates the rest of the pipeline too, skipping parsing and merging entirely for a domain with nothing new.

### Automated ingest pipeline (CI)

The monthly refresh described above is implemented in `.github/workflows/ingest.yaml`, which runs end-to-end against a long-lived `ingest` branch, on a monthly cron (`0 6 1 * *`) and on every push to `ingest`.

Each run merges the latest `main` into `ingest`, then runs `poetry run ingest`. If any subdivision orphans remain, `ingest_subdivisions()`'s hard gate (see Pipeline integration above) calls `sys.exit(10)` before anything is staged, so this step itself fails the job, visible as a red X in the Actions tab, with the exact orphan counts in its log output. Nothing downstream (version bump, commit, push, PR) runs in that case, and the `ingest` branch is left untouched; resolving it is a local step: pull `ingest`, run the resolve-subdivisions skill, commit, and push back to `origin/ingest`, which re-triggers this workflow through its push trigger.

A clean run then regenerates `tests/analysis/data_stats.json` and fills the docs' stat markers from it (see Performance Profile), so the record counts and resolution breakdown in the README and `methodology.md` always describe the data being committed; the test suite's `render_docs.py --check` fails a run whose docs don't. Locally, `poetry run analysis --data-only` does the same after an ingest. Timing and memory figures aren't regenerated in CI, since they depend on the host: after a change that could move them, run the whole suite with `poetry run analysis --notes "what changed"`, which runs the data stats, footprint and benchmarks and then fills the markers. `poetry run analysis --check` only checks that the docs' deterministic markers are current.

It stages whatever changed. If `src/localis/data` (the published dataset) changed, it bumps the **patch** version with `poetry version patch` before committing. A data refresh doesn't touch the public API, so minor is reserved for genuine backward-compatible additions; conflating the two would mean a consumer reading `1.4.0 → 1.5.0` couldn't tell "just fresher data" from "there's a new method worth checking out." Freshness is still visible, just through the CHANGELOG's per-release counts rather than the version number itself. Bookkeeping files (the per-domain `*.manifest.json`, `resolution_map.json`) can change independently of the dataset output and still get committed on a run where the dataset itself didn't move. Everything staged is committed and pushed back to `ingest`, then a single, persistent `ingest` → `main` pull request is created (ready for review, not draft, since reaching this point already guarantees a clean, orphan-free run) or, if it already exists, commented with that run's actual diff (`git diff --stat HEAD~1 HEAD -- src/localis/data`), so the PR reads as a log of real changes rather than a bare pointer at commit history.

One bug this surfaced and fixed in passing: `release.yaml`'s checkout step never fetched tags, so its `git tag | sort --version-sort | tail -n1` always came back empty. The workflow believed no version had ever shipped and re-attempted publishing whatever version was already in `pyproject.toml`, which is what actually broke the most recent release (PyPI rejects re-uploading an already-used filename), not a PyPI API change as it first appeared. Fixed with `fetch-tags: true` on that checkout step, which matters here specifically because a merged `ingest` PR is exactly the kind of push to `main` that would retrigger this failure mode.

## Performance Profile

Every figure in this section and in the README's Performance section is generated, never transcribed by hand. `tests/analysis/data_stats.py` produces the deterministic numbers (record counts, the subdivision resolution breakdown, shipped file sizes) into `data_stats.json`, and asserts that they reconcile. `tests/analysis/footprint.py` measures load time and retained memory per registry component, each scenario in fresh subprocesses with the median kept, and `tests/analysis/benchmarks.py` measures per-call latency percentiles and search accuracy; both append to a history (`footprint.json`, `benchmarks.json`) with a fingerprint of the host they ran on. `tests/analysis/render_docs.py` fills each `stat:source.key|format` HTML-comment marker in the docs from those files, and `render_docs.py --check`, run by the test suite, fails if a deterministic marker is stale. Current figures were measured on <!-- stat:footprint.host.cpu|raw -->-<!-- /stat --> with Python <!-- stat:footprint.host.python|raw -->-<!-- /stat -->. Memory figures are retained RSS deltas (`VmRSS` read from `/proc/self/status` after an explicit `gc.collect()`), not `ru_maxrss` peak; see Memory measurement methodology below for why that distinction matters.

### Search and filter index architecture

Both indexes moved off `list[int]` postings (each id a full boxed Python object, ~36 bytes) onto `array.array("I", ...)` (packed 4-byte unsigned ints), for the same reason in both cases: the cost was in the container, not the data.

The search index also changed format on disk. It used to be one TSV line per trigram, `base64(varint(delta(ids)))`, which requires a serial, byte-at-a-time Python loop to decode, that can't be bulk-loaded regardless of the target container. It's now two files: `search_index.bin.gz` (every trigram's sorted ids, packed as raw uint32, concatenated in one buffer, gzip'd as a whole) and `search_index_offsets.tsv` (`trigram, offset, count`, offset/count in id-count units, plain text since it's small and worth keeping git-diffable). Loading decompresses and `array.frombytes()`s the entire blob in one bulk call, then slices per-trigram arrays out of that single decoded array using the offsets table, decode once, slice many, rather than decoding per trigram.

The filter index's fix didn't need a format change, just the container: `FilterIndex.load()` builds its reverse index (`value -> ids`) entirely in memory from per-entity rows already on disk, there was never a variable-length encoding to redesign, so swapping the `defaultdict(list)` factory for `defaultdict(lambda: array("I"))` was the whole change.

### Subdivision hashid

`SubdivisionModel.hashid` is an MD5-derived id used only during ingestion (merging ISO and GeoNames records, and supporting the resolve-subdivisions skill). It used to be computed in `__post_init__`, which runs on every construction, including the normal runtime `_cache` load, where nothing ever reads `hashid`, it's discarded once a subdivision has been merged. `set_hashid()` is now an explicit method, called only at the two ingestion sites that actually need it (`ingest/subdivisions/scripts/geonames_subdivisions.py`, `ingest/subdivisions/scripts/iso_subdivisions.py`); `SubdivisionModel.from_row()`, the runtime path, never calls it. Subdivisions' dataset load dropped from 289.5ms to 98.7ms (−66%) as a result.

### Memory measurement methodology

Earlier benchmarks in this document used `resource.getrusage(resource.RUSAGE_SELF).ru_maxrss`, the process's historical peak resident memory, which only ever increases and never reflects memory freed later in the same process. That overstates any component whose loading path allocates a large transient buffer it doesn't keep: `SearchIndex.load()` decompresses its entire gzip blob into one big `array("I")` before slicing per-trigram arrays out of it (a copy, not a view), so the decompression peak gets permanently recorded by `ru_maxrss` even after that buffer is freed and unmapped moments later. Re-measuring with actual post-GC retained memory (`VmRSS` after `gc.collect()`) showed cities' search index really retains about a third of its previously documented figure (33.5MB vs. 96.8MB), while cache and filter index numbers, which don't have this transient-buffer pattern, held up closely under both methodologies. All numbers below use the retained methodology.

### Shipped data size

`src/localis/data/` is <!-- stat:data.shipped_size.total|size -->57.0MB<!-- /stat --> total, almost entirely cities:

| Domain | Size | Share |
|---|---|---|
| Countries | <!-- stat:data.shipped_size.countries.total|size -->73KB<!-- /stat --> | <!-- stat:data.shipped_size.countries.share_pct|pct -->0.1%<!-- /stat --> |
| Subdivisions | <!-- stat:data.shipped_size.subdivisions.total|size -->10.6MB<!-- /stat --> | <!-- stat:data.shipped_size.subdivisions.share_pct|pct -->18.5%<!-- /stat --> |
| Cities | <!-- stat:data.shipped_size.cities.total|size -->46.4MB<!-- /stat --> | <!-- stat:data.shipped_size.cities.share_pct|pct -->81.4%<!-- /stat --> |

Within cities: `cities.tsv` <!-- stat:data.shipped_size.cities.files.cities.tsv|size -->12.6MB<!-- /stat -->, `filter_index.tsv` <!-- stat:data.shipped_size.cities.files.filter_index.tsv|size -->17.5MB<!-- /stat -->, `search_index.bin.gz` <!-- stat:data.shipped_size.cities.files.search_index.bin.gz|size -->12.8MB<!-- /stat -->, `search_index_offsets.tsv` <!-- stat:data.shipped_size.cities.files.search_index_offsets.tsv|size -->234KB<!-- /stat -->, `lookup_index_int.tsv` <!-- stat:data.shipped_size.cities.files.lookup_index_int.tsv|size -->3.2MB<!-- /stat -->.

### Memory footprint

| Registry (`force_cache()`) | Retained memory |
|---|---|
| countries | <!-- stat:footprint.registries.countries.combined.memory_bytes|size -->-<!-- /stat --> |
| subdivisions | <!-- stat:footprint.registries.subdivisions.combined.memory_bytes|size -->-<!-- /stat --> |
| cities | <!-- stat:footprint.registries.cities.combined.memory_bytes|size -->-<!-- /stat --> |
| **total, all three fully cached** | **<!-- stat:footprint.full_cache.memory_bytes|size -->-<!-- /stat -->** |

Cities' <!-- stat:footprint.registries.cities.combined.memory_bytes|size -->-<!-- /stat --> breaks down further by structure:

| Cities component | Retained memory | Build time |
|---|---|---|
| `_cache` | <!-- stat:footprint.registries.cities.dataset.memory_bytes|size -->-<!-- /stat --> | <!-- stat:footprint.registries.cities.dataset.time_ms|load -->-<!-- /stat --> |
| `_lookup_index` | <!-- stat:footprint.registries.cities.lookup_index.memory_bytes|size -->-<!-- /stat --> | <!-- stat:footprint.registries.cities.lookup_index.time_ms|load -->-<!-- /stat --> |
| `_filter_index` | <!-- stat:footprint.registries.cities.filter_index.memory_bytes|size -->-<!-- /stat --> | <!-- stat:footprint.registries.cities.filter_index.time_ms|load -->-<!-- /stat --> |
| `_search_index` | <!-- stat:footprint.registries.cities.search_index.memory_bytes|size -->-<!-- /stat --> | <!-- stat:footprint.registries.cities.search_index.time_ms|load -->-<!-- /stat --> |

**Total load time** (all three registries, `_cache` plus every index) is <!-- stat:footprint.full_cache.time_ms|load -->-<!-- /stat -->.

### Population floor

`CityRegistry.set_population_threshold(n)` narrows the cache and all three indexes to cities with population >= n, implemented via two predicate protocols in `localis/utils/data.py`: `CacheFilterPredicate` (`row -> bool`, evaluated inline as `CityView.load()` parses each TSV row, since population is only known once that row is parsed) and `IndexFilterPredicate` (`(id, allowed_ids) -> bool`, the shared membership check `Registry._is_id_allowed()` implements for `FilterIndex`/`SearchIndex`/`LookupIndex`, none of which have population data of their own and can only ever ask "is this id still allowed"). `CityRegistry.build_cache()` derives `self._allowed_ids` as a byproduct of the `CityView.load()` pass it already has to do; `Registry._lookup_index`/`_filter_index`/`_search_index` force `self._cache` before building, guaranteeing `_allowed_ids` reflects the current threshold, since none of the three indexes have any real use without the cache regardless of population filtering.

Ids stay stable across thresholds. `Store.id_to_idx` (an `array.array("i")` sized to the full unfiltered id space, `-1` for an excluded id) decouples a View's physical position in its Store from its public `id`, so `View._idx` resolves through this array instead of assuming `id - 1`. That lets `CityStore` skip allocating rows for excluded cities entirely, a real memory saving rather than just fewer View wrapper objects, without ever renumbering an id a caller might already be holding.

At a <!-- stat:data.cities.threshold|int -->15,000<!-- /stat --> threshold (the tier geonamescache ships as a separate bundled dataset), cities drops from <!-- stat:data.cities.total|int -->235,914<!-- /stat --> to <!-- stat:data.cities.above_threshold|int -->34,171<!-- /stat --> and retained memory drops from <!-- stat:footprint.registries.cities.combined.memory_bytes|size -->-<!-- /stat --> to <!-- stat:footprint.cities_threshold.memory_bytes|size -->-<!-- /stat -->.
