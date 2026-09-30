# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `py.typed` marker (PEP 561)
- `CityRegistry.set_population_threshold(n)` / `get_population_threshold()`, narrowing the cities cache and all three indexes to population >= n, w E2E tests.

### Fixed
- Type hint discrepancies across `entities`/`views`/`stores`/`registries`/`indexes` (nullable fields, `View`/`Store` generics, `Mapping` covariance); `src/localis` now passes `pyright` with zero errors
- Cities' documented search index memory was measured via `ru_maxrss` (peak, not retained); corrected to post-GC `VmRSS`, dropping the documented figure from 96.8MB to 33.5MB

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