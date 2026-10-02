# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.0.0] - 2026-10-02

### Breaking
- `City.admin1`/`City.admin2` removed; use `City.subdivisions`, ordered by `admin_level`
- `SubdivisionBase` has a new required `admin_level` field
- Historic (ISO 3166-3) countries are excluded from `filter()`/`search()`/iteration unless `include_historic` is set, and `lookup()` resolves them only by `alpha_4`

### Added
- `Country.historic: HistoricInfo | None` for ISO 3166-3 withdrawn/historic countries (Czechoslovakia, Serbia and Montenegro, Netherlands Antilles, and 28 others), adding 31 historic entries to the dataset (281 total countries, 250 active); `CountryRegistry.include_historic` toggle (default `False`) excludes them from `filter()`/`search()`/iteration, never from `get()`/`lookup()`. Since ISO reused alpha2/alpha3/numeric codes across different withdrawn countries over time (e.g. `CS`: Czechoslovakia, then later Serbia and Montenegro), `lookup()` only resolves a historic entry by its unique `alpha_4` withdrawal code
- `geonames_id` on `CountryModel`/`Country` (ingestion-side and runtime)
- `py.typed` marker (PEP 561)
- `CityRegistry.set_population_threshold(n)` / `population_threshold` property, narrowing the cities cache and all three indexes to population >= n, w E2E tests.
- `geonames_id` on `SubdivisionModel` (ingestion-side)
- `admin_level=0` for ISO subdivision entries that are documentation/statistical groupings rather than real administrative divisions (Indonesia's island-grouping "Geographical unit" tier, the Dominican Republic's planning "Region" tier, Cabo Verde's "Geographical region"); these bypass GeoNames merging entirely and their real `parent` reference is preserved
- Wikidata crosswalk (P300 ISO code ↔ P1566 GeoNames id) as a subdivision resolution source, applied ahead of auto-merge; resolved ~3900 subdivisions unambiguously on its own in its first run, cutting auto-merge's workload by ~90% and orphans by ~60%
- Generated documentation numbers: `tests/analysis/data_stats.py` (record counts, subdivision resolution breakdown, shipped sizes, with reconciliation asserts), `footprint.py` (load time and retained memory per registry component, median of fresh-process runs) and a retooled `benchmarks.py` (get/lookup/filter/search latency p50/p95/p99/max and search accuracy, reproducible seeds) write JSON, the latter two with a host fingerprint; `render_docs.py` fills `stat:` markers in the README, `methodology.md` and `dev.md` from them, and a test fails when a deterministic marker is stale. All of it runs as one command, `poetry run analysis` (`--data-only` for the deterministic part, `--check` to only verify the docs); the ingest workflow runs `--data-only` after every ingest
- `docs/unmerged_subdivisions.md`, regenerated from the final dataset on every ingest run: every ISO 3166-2 subdivision with no `geonames_id`. 203 of 5,046 currently unmerged after a full skill + ingest run

### Changed
- resolve-subdivisions candidates are now a list ranked best first; they were an ID-keyed dict whose keys got sorted in transit, losing the ranking within every batch. The skill's context reset is now an estimated token budget instead of a 1000-candidate count
- Automerge margin floor: a winning pair less than 5 points over its threshold becomes a `low_margin` orphan for the skill to confirm instead of merging (`MG-D` and `TW-TNN` were wrong merges at margins 1 and 3)
- Skill decisions can no longer overrule Wikidata silently: one that disagrees with a valid Wikidata mapping it wasn't made against becomes a `wikidata_conflict` orphan for review, and each decision records the mapping it saw (`wikidata_seen`) along with its `reason`, `decided_by` and escalation findings; the old `resolution_log.txt` and `review_output.json` are folded into `resolution_map.json`, whose `skill_resolved`/`auto_merge` keys are renamed `skill_decisions`/`automerge`, with `skill_decisions` and `wikidata_merge` flattened to plain code-keyed maps
- Every skill decision must carry a reason and its decider (agent or human), `merge` included; the 293 of 324 existing decisions that lacked them were cleared for re-resolution under the current rules. The skill's accepted reasons for "no counterpart" are now written into its instructions (different administrative scheme, territory GeoNames treats as its own country, subdivision retired by a merger or split, disputed territory), and it may no longer apply rules from memory
- resolve-subdivisions skill's accepted patterns now include Monaco's quarters (GeoNames has one record for the whole municipality) and cities with their own administrative status (Hungary's cities with county rights, Thailand's Pattaya), never merged into the district containing them; places too new for GeoNames still always go to a human. The skill requires Opus 5.5 or stronger, after Sonnet 5 runs left wrong merges and duplicates. Its full re-run brought merged ISO subdivisions from 4,751 to 4,843 of 5,046 and ISO-only records from 295 to 203
- 18 Hungarian cities with county rights that the skill had merged into their járás (a larger district) are now ISO-only records, so each district stays a GeoNames record under its county
- resolve-subdivisions skill sees every subdivision in the orphan's country with claimed records, type mismatches and directional mismatches marked rather than hidden (the directional guard had hidden `GD-10` "Southern Grenadine Islands" from its only match, "Carriacou and Petite Martinique"), `add` requires a concrete reason, and explicit escalation criteria send claimed-record conflicts, ties, partial mappings and unexplained absences to a human, who picks the decision and its reason from two question prompts
- ISO subdivisions of a country with no GeoNames subdivisions at all (Singapore) are added as-is by automerge on every run (`automerge.geonames_absent`) instead of orphaned, so they merge automatically if GeoNames ever adds records
- Guinea-Bissau's provinces (Leste, Norte, Sul) are non-administrative groupings bypassed at `admin_level=0`, reversing an unverified ruling that treated them as a real level; its regions are now level 1, matching GeoNames
- The Marshall Islands' Ralik and Ratak chains are non-administrative groupings bypassed at `admin_level=0`, so the 24 municipalities are level 1, matching GeoNames
- Ingest logs are tracked and no longer timestamped, so a log only changes when an ingest run's output does
- `City.admin1`/`admin2` (fixed fields, admin levels 1-2 only) replaced with `City.subdivisions: list[SubdivisionBase]`, ordered by admin_level ascending, representing the full administrative chain including level 0 (documentation/statistical groupings) and any 3rd+ generation tiers GeoNames itself never nests to; `SubdivisionBase` gained `admin_level` so list entries are distinguishable by level. `CityModel.FILTER_FIELDS` flattens every level into the filter index; `SEARCH_FIELDS` keeps only the admin_level=1 entry, matching its prior footprint, to avoid bloating the trigram index with every level's name
- `CityStore`'s subdivision ids are packed into a flat `array('I')` blob with parallel offset/count arrays, the same scheme the search index already uses for trigram postings, instead of a `list[list[int]]`, which at 235k+ rows added ~35MB (+59%) to cities' dataset memory from pure per-row Python object overhead
- All registries (`Country`, `Subdivision`, `City`) are now lazy-loaded on first access; `Country`/`Subdivision` previously eager-loaded on import
- Restructured `ingest/`: per-domain `raw/` split into `inputs/`/`outputs/`/`logs/`; new `ingest/shared/` package for cross-domain models, loaders, and fetch (GeoNames alternate names, CLDR)
- Rewrote subdivision auto-merge: excludes already-claimed candidates, assigns globally by best score instead of first match, excludes targets where multiple ISO subs both score highly (namesake collisions), switched `token_set_ratio` to `token_sort_ratio` to stop subset-match false positives, expanded categorical token stripping
- `resolve-subdivisions` skill and `resolution_map.json` now key on `geonames_id` instead of an unstable per-run hash; `resolution_map.json` simplified to a flat `dict[str, int | None]`
- Overhauled ingest logging: per-domain log files, log levels, per-merge/orphan diagnostics
- Subdivision aliases enriched from GeoNames' `alternateNamesV2` dump (English + each country's CLDR official language(s) only, historic/colloquial/bidi-control names excluded), feeding into fuzzy matching
- `resolution_map.json` restructured from a flat per-code cache into the single source of truth for every subdivision's resolution, not just the ones needing human help: nested by how each was decided (`automerge`, `skill_decisions`, `wikidata_merge`, `bypassed`), with `automerge` results recomputed on every run so a stale decision is replaced automatically, no manual cache-invalidation step required; `orphaned_subdivisions.json` is retired, orphans (`no_candidates`/`no_matches`/`ambiguity`) now live in this same file
- Subdivision fuzzy-match threshold no longer gives single-token names an extra discount on top of the length-based one; it was stacking with short-name leniency to let coincidental shared suffixes (e.g. "Enfield"/"Wakefield", both ending in "-field") clear threshold despite sharing no real resemblance
- Ingest log files renamed from `*_ingest_log.txt` to `*_ingest.log`
- Subdivision auto-merge now disqualifies candidate pairs where the GeoNames side's raw qualifier words mark it as a city but the ISO side's `type` isn't (or vice versa), preventing confident-but-wrong string matches (e.g. a city ISO code stealing its containing oblast/county/department's GeoNames entry); renamed `CATEGORICAL_TOKENS` to `NOISE_TOKENS`, grouped into two families (`city` vs `area`) rather than granular ones, since finer administrative-type distinctions aren't reliable across sources/translations
- ISO subdivision names with trailing `[...]`/`(...)` content (alternate-language names, embedded codes, territory-dispute annotations) are now split at load time: genuine alternate names become aliases, codes/annotations/duplicates are dropped, instead of polluting fuzzy-match comparisons inline
- `admin_level` is now computed by walking the full ISO parent chain instead of a one-level-deep check capped at 2, so a genuine 3rd+ generation (so far only France's régions → collectivités → départements) gets its own level instead of colliding with its parent's; non-administrative ancestors stay transparent and don't count toward depth
- Split `merge_subdivisions.py` into `ingest/subdivisions/scripts/automerge/` (`type_families`, `directional`, `names`, `merge`, `scoring`, `try_merge`); extracted `candidate_pool()`/`score_candidates()` as shared primitives now used identically by `try_merge` and the resolve-subdivisions skill
- `try_merge` now buckets ISO entries at admin_level 2 and 3+ together, since both draw from GeoNames' same level-2-capped data; previously they competed in separate buckets, leaving any 3rd-generation entry (France's départements) permanently unmatchable even against a valid target
- `Orphans.ambiguity` now stores `AmbiguousOrphan(iso_code, candidate_geonames_ids)` per orphan instead of a flat iso_code list, so the specific contested GeoNames targets survive past the run that found them
- resolve-subdivisions skill candidate provisioning is now bucket-aware: `no_candidates` orphans fall back to the whole country instead of just the matching admin_level; `ambiguity` orphans see only the flagged close-calls first, falling through to the normal pool (those excluded) only if rejected; `no_matches` unchanged
- resolve-subdivisions `SKILL.md`: merged the self-certified "add without searching" step into the websearch step, so an orphan with no fitting candidate is always researched before merge/add/escalate is decided
- Estonian `vald`/`linn` qualifier words added to the type-family token sets (`vald`→area, `linn`→city); GeoNames' raw Estonian names append these and they weren't being stripped before fuzzy comparison
- `ingest_subdivisions()` now hard-fails (logs the orphan counts, `sys.exit(10)`) if any subdivision orphans remain after a run, before dumping subdivisions or handing its geocode map to cities ingestion; `.github/workflows/ingest.yaml` simplified accordingly, the `ingest` step itself now fails the job on orphans and nothing downstream (commit/push/PR) runs, so the automated `ingest` → `main` PR is now created ready for review directly instead of as a draft that needed a separate orphan check to mark ready
- CI: ingest merges from and opens PRs against `dev` instead of `main`, runs pyright/pytest before opening its PR, and only patch-bumps when the current version is already released; Test runs pyright, runs ingest on `dev` pushes (failing on any uncommitted dataset change), and gates PRs to `main`; Release publishes the exact commit Test passed and skips versions that are already tagged

### Removed
- `resolution_map.json`'s `audited` record and `ResolutionMap.reconcile()`, which were never populated; the planned audit system replaces them with fingerprinted verdicts that are kept, not deleted, when superseded
- Ipregistry as a data source; its 219 `localVariant` subdivision aliases carried CC BY-SA 4.0 share-alike terms for little gain over GeoNames' alternate names
- Manual alias/name contribution during subdivision resolution (CLI and skill); resolutions are now source-data only
- Deprecated interactive CLI subdivision resolver, fully superseded by the resolve-subdivisions skill
- `ingest/subdivisions/scripts/check_orphans.py` and the `check-orphans` poetry script, superseded by `ingest_subdivisions()`'s own hard exit-10 gate on active orphans

### Fixed
- An ingest run that found orphans exited before anything was committed, so its orphan queue was lost with the runner and the documented recovery (pull `ingest`, run the skill) had nothing to resolve. The workflow now commits the orphan queue and logs to `ingest` before failing, and the recovery steps include `poetry run ingest --force` to fetch the sources locally
- `load_countries()` keyed historic countries by their reused alpha-2 codes, so they overwrote Anguilla, Bonaire, Belarus, Georgia and Slovakia (and one CS entry overwrote the other); standalone subdivision or city ingest then failed on missing country ids or silently attached those countries' subdivisions to withdrawn ones, and the resolve-subdivisions skill showed the agent the wrong country name. Historic rows are now keyed by alpha-4, matching `ingest_countries()`
- A GeoNames-only subdivision's `admin_level` is now one below its parent's instead of a fixed 2 for any record with a parent, which had put 63 districts in Iraq's Kurdistan governorates and Equatorial Guinea's provinces at the same level as their level-2 parents, and would have left a level gap under non-administrative groupings' twins (Ireland's councils such as Fingal are now level 1, beside the ISO-merged counties)
- A non-administrative grouping now merges into its GeoNames twin (the level-1 record all its merged children sit under: Lithuania's counties, Iceland's regions, Ireland's provinces, Malawi's regions) instead of leaving it in automerge's pool as a GeoNames-only duplicate; automerge had matched `LT-54` (Utena district municipality) to Utena County, now corrected to the municipality's own record. When the twin can't be identified before automerge runs, an automerge result into it is sent back as a `grouping_twin` orphan instead of shipping
- Type hint discrepancies across `entities`/`views`/`stores`/`registries`/`indexes` (nullable fields, `View`/`Store` generics, `Mapping` covariance); `src/localis` now passes `pyright` with zero errors
- Cities' documented search index memory was measured via `ru_maxrss` (peak, not retained); corrected to post-GC `VmRSS`, dropping the documented figure from 96.8MB to 33.5MB
- Ingest source change detection (`has_changed()`) falsely flagged unchanged files as changed due to unreliable `Last-Modified`/`Content-Length` HEAD headers; now compares `ETag` only
- `has_changed()` no longer trusts the manifest when the tracked file is actually missing on disk
- `SubdivisionMap.refresh()` no longer overwrites a merged subdivision's ISO-derived `admin_level` with one re-derived from GeoNames' own parent nesting, which could silently corrupt it after merge
- ISO subdivisions whose real admin_level-1 parent was misidentified as a real second admin tier (e.g. Indonesia's provinces nested under a non-administrative grouping) now compute the correct level
- resolve-subdivisions skill's `get_geonames_submap()` never replayed already-recorded resolutions (`skill_decisions`/`wikidata_merge`/`automerge.resolutions`) onto its own fresh GeoNames map, so an already-claimed target could still appear as a valid, unclaimed candidate and pass `is_valid_candidate()`
- resolve-subdivisions skill was missing GeoNames alternate-name enrichment on its candidate pool, showing weaker name variants than auto-merge itself uses
- `load_countries()`/`load_subdivisions()`, the fallback loaders used when subdivisions or cities ingest runs standalone, read the wrong columns and skipped type coercion; `load_subdivisions()` crashed on its first call
- Type errors across `ingest/` and `tests/`; the whole repo now passes `pyright`, enforced in CI
- 77 places shipped twice, an ISO-only record beside a GeoNames-only twin (Bayern/Bavaria, Hamburg, most Icelandic and Lithuanian municipalities); all 251 "no counterpart" skill decisions cleared for re-resolution
- `RU-AL`/`RU-ALT` swapped by a stale skill decision; Wikidata's mapping now applies
- Merged subdivisions kept GeoNames' parent instead of ISO's
- Kosovo's `numeric` was `0` instead of `None`
- `search_index.bin.gz` changed bytes on every dump even with identical data (gzip embeds the current time), which made CI's dataset-change check fire on every run
- Country ingest crashed on Python versions before 3.14 (a bare `super()` call inside a slotted dataclass), and the ingest logger crashed when its `logs/` folder didn't exist yet

## [1.1.2] - 2026-09-29

### Changed
- Automated data ingest pipeline now version-bumps patch instead of minor
- Rearchitected the search index (gzip'd fixed-width id blob + offsets table, replacing per-trigram base64/varint/delta encoding) and the filter index (`array.array` postings instead of `list[int]`), cutting total package memory footprint by 48% (1134MB → 587MB peak) and total load time by ~37% (~4.3s → ~2.7s); cities' search index specifically dropped 70% in memory and became 5.2x faster to build
- Stopped computing subdivisions' ingestion-only `hashid` at normal runtime load (it's now set explicitly only where ingestion needs it), cutting subdivisions' dataset load time by 66% (289.5ms → 98.7ms); also cached `Model.extract_base()`'s per-class field lookup instead of recomputing it on every `to_dto()` call (−45% on a mixed `filter()`/`lookup()` workload) and upgraded `rapidfuzz` past a version whose lock predated Python 3.14 wheels, restoring its compiled extension (search queries −35%)
- Switched the shipped cities dataset from GeoNames' full `allCountries.txt` export to its pre-filtered `cities500.txt`, cutting cities from 472,613 to 235,895 and the shipped `src/localis/data/` size from 98MB to 54MB
- Replaced the `Model`/`DTO` class hierarchy with three independent layers: `Entity` (renamed from `DTO`), `View`, and `Store` (its own `stores/` package). `Model` moved out of the shipped package into the `ingest/` pipeline (renamed from `data/`); both `localis/` and `ingest/` now use `__init__.py`-mediated package-level imports throughout.
- ISO 3166-2 subdivision data now comes from Debian's iso-codes instead of Ipregistry; Ipregistry is used only for its `localVariant` alias enrichment
- Cruft and legacy code removed from the codebase

## [1.1.1] - 2026-09-28

### Changed
- Minor README updates

## [1.1.0] - 2026-09-28

### Changed
- Ran the automated ingestion pipeline for the first time, refreshing the shipped dataset
  - Countries: 249 -> 254
  - Subdivisions: 51,541 -> 51,684
  - Cities: 451,792 -> 472,613

## [1.0.0] - 2026-09-28

### Added
- `resolve-subdivisions` Claude Code skill and MCP server for resolving ISO/GeoNames subdivision merge orphans, with human escalation for genuinely ambiguous cases
- Checksum-aware source fetching: skips download, parsing, and merging for a domain when none of its sources have changed since the last run
- CI: automated monthly ingest pipeline workflow, gated on orphan resolution, with draft PR automation
- Developer guide (`docs/dev.md`)

### Changed
- Rewrote the ingestion pipeline to fetch current source data end-to-end

### Fixed
- Registry search and filter bugs, and type mismatches
- Inaccessible cache in the subdivisions registry
- Country aliasing and contemporary name mappings
- Silent dropping of non-ISO countries during ingest
- Indeterminate set ordering in the countries filter index
- Line-ending inconsistencies in dataset TSVs that broke CI diff checks

### Removed
- Dead CLI code path

## [1.0.0a3] - 2025-12-05

### Changed
- Migrated from SQLite to TSV-based, lazy loading architecture for improved performance
- Reduced eager cold start time to 1.1s for full dataset
- Improved search accuracy: Countries 100%, Subdivisions 94%, Cities 99%

### Added
- Trigram-based fuzzy search with 30ms average query time
- Lazy-loaded indexes

### Removed
- Deprecated old SQLite backend
- CLI
- Downloading and copying of db with cities dataset
- Subdivisions
  - `for_country` method removed
  - `types_for_country` method removed (may be added again)
- Cities
  - `for_subdivision` method removed
  - `for_country` method removed


## [1.0.0a2] - 2025-11-22

### Added
- Initial alpha release
- Support for 249 countries, 51k subdivisions, 451k cities
- Lookup, filter, and search APIs
- sqlite3 backend with FTS5 for full-text search
- Basic fuzzy matching capabilities
- Comprehensive test suite
- GitHub CI/CD Workflows