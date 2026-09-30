# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `py.typed` marker (PEP 561)
- `CityRegistry.set_population_threshold(n)` / `population_threshold` property, narrowing the cities cache and all three indexes to population >= n, w E2E tests.
- `geonames_id` on `SubdivisionModel` (ingestion-side)
- `admin_level=0` for ISO subdivision entries that are documentation/statistical groupings rather than real administrative divisions (Indonesia's island-grouping "Geographical unit" tier, the Dominican Republic's planning "Region" tier, Cabo Verde's "Geographical region"); these bypass GeoNames merging entirely and their real `parent` reference is preserved

### Changed
- All registries (`Country`, `Subdivision`, `City`) are now lazy-loaded on first access; `Country`/`Subdivision` previously eager-loaded on import
- Restructured `ingest/`: per-domain `raw/` split into `inputs/`/`outputs/`/`logs/`; new `ingest/shared/` package for cross-domain models, loaders, and fetch (GeoNames alternate names, CLDR)
- Rewrote subdivision auto-merge: excludes already-claimed candidates, assigns globally by best score instead of first match, excludes targets where multiple ISO subs both score highly (namesake collisions), switched `token_set_ratio` to `token_sort_ratio` to stop subset-match false positives, expanded categorical token stripping
- `resolve-subdivisions` skill and `resolution_map.json` now key on `geonames_id` instead of an unstable per-run hash; `resolution_map.json` simplified to a flat `dict[str, int | None]`
- Overhauled ingest logging: per-domain log files, log levels, per-merge/orphan diagnostics
- Subdivision aliases enriched from GeoNames' `alternateNamesV2` dump (English + each country's CLDR official language(s) only, historic/colloquial/bidi-control names excluded), feeding into fuzzy matching
- Subdivision auto-merge now disqualifies candidate pairs where the GeoNames side's raw qualifier words mark it as a city but the ISO side's `type` isn't (or vice versa), preventing confident-but-wrong string matches (e.g. a city ISO code stealing its containing oblast/county/department's GeoNames entry); renamed `CATEGORICAL_TOKENS` to `NOISE_TOKENS`, grouped into two families (`city` vs `area`) rather than granular ones, since finer administrative-type distinctions aren't reliable across sources/translations
- ISO subdivision names with trailing `[...]`/`(...)` content (alternate-language names, embedded codes, territory-dispute annotations) are now split at load time: genuine alternate names become aliases, codes/annotations/duplicates are dropped, instead of polluting fuzzy-match comparisons inline

### Removed
- Manual alias/name contribution during subdivision resolution (CLI and skill); resolutions are now source-data only
- Deprecated interactive CLI subdivision resolver, fully superseded by the resolve-subdivisions skill

### Fixed
- Type hint discrepancies across `entities`/`views`/`stores`/`registries`/`indexes` (nullable fields, `View`/`Store` generics, `Mapping` covariance); `src/localis` now passes `pyright` with zero errors
- Cities' documented search index memory was measured via `ru_maxrss` (peak, not retained); corrected to post-GC `VmRSS`, dropping the documented figure from 96.8MB to 33.5MB
- Ingest source change detection (`has_changed()`) falsely flagged unchanged files as changed due to unreliable `Last-Modified`/`Content-Length` HEAD headers; now compares `ETag` only
- `has_changed()` no longer trusts the manifest when the tracked file is actually missing on disk
- `SubdivisionMap.refresh()` no longer overwrites a merged subdivision's ISO-derived `admin_level` with one re-derived from GeoNames' own parent nesting, which could silently corrupt it after merge
- ISO subdivisions whose real admin_level-1 parent was misidentified as a real second admin tier (e.g. Indonesia's provinces nested under a non-administrative grouping) now compute the correct level

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