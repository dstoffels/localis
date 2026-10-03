# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Upgrading from 2.0.0
- `Country.name` is now ISO 3166-1's name as published ("Korea, Republic of"); use `Country.common_name` for the everyday name ("South Korea")
- `filter()` raises `TypeError` for a keyword argument the registry can't filter by, where it returned `[]`
- `localis.registries.Registry` is now the lookup-only base; type-hint `QueryableRegistry` where `filter()` or `search()` is called

### Added
- `Country.common_name`: the short name in everyday use, from Debian iso-codes ("South Korea", "Iran", "Taiwan"), or `None` where it has none; searchable and filterable, including through the `country` filter on subdivisions and cities
- `localis.macroregions`: Unicode CLDR's world regions, 34 in all: 5 regions (Africa, Americas, Asia, Europe, Oceania), 23 subregions and 6 groupings (North America, Latin America, Sub-Saharan Africa, European Union, Eurozone, United Nations), each with its CLDR code, English name, type and parent. Lookup-only: `get()`, `lookup()` by code or name (M49 codes are zero-padded strings, so `lookup("009")` finds Oceania), iteration and `len()`
- `Country.macroregions`, the country's CLDR path as `(region, subregion)`, and `Country.groupings`, the groupings it belongs to, both `tuple[MacroregionBase, ...]`. Every current country is placed; historic countries take only CLDR's placements for withdrawn codes, which cover 10 of 31
- `countries.filter(macroregion=...)`, matching any region, subregion or grouping in a country's path or groupings, by name or code

### Changed
- Development moved from Poetry to uv, with dev commands as poethepoet tasks (`poe ingest`, `poe analysis`, `poe test`); the package is built with hatchling, with the same wheel contents
- Country aliases from Wikidata are queried live instead of read from `wiki_countries.json`, an undocumented hand-made snapshot that has been removed: each ISO alpha-2 item's English label, alternative labels and short names (P1813, which supplies abbreviations such as USA, DRC, ROK and UAE), with the most-linked item kept where a code is shared. Names are filtered mechanically: a leading "the" is dropped, anything containing a digit, slash or symbol is rejected, and names of three characters or fewer are kept only as uppercase abbreviations that aren't ISO codes, so UK, DRC and ROC are kept while language codes and ISO codes are not. The item's own IOC and FIFA codes, ISO 3166-2-shaped codes and non-Latin names are dropped; nicknames, demonyms, misspellings and stray codes that no rule identifies are listed with reasons in `ingest/countries/inputs/name_blocklist.json`; and an alias shared by two current countries is dropped from both. Historic countries and Kosovo are enriched from the same query
- `localis.registries.Registry` is now the lookup-only base (`get()`, `lookup()`, iteration); `filter()` and `search()` moved to its new subclass `QueryableRegistry`, which the countries, subdivisions and cities registries extend
- `filter()` raises `TypeError` for a keyword argument the registry can't filter by, instead of silently returning `[]`
- Lookup index files with no entries are no longer shipped (cities' string index, subdivisions' integer index)
- Search reworked around its trigram index: each record's names (name, aliases, codes) and its context (parent, admin1, country) are indexed separately, and query and index share one normalization (punctuation as spaces, padded word trigrams). Query trigrams are weighted by rarity. Canon and context hits are counted in C, skipping trigrams shared by more than 2% of records, and the 200 records with the most hits get their exact rarity-weighted coverage; a one-word query of 6 characters or fewer also takes its closest matches by edit distance from a shipped list of short names (countries and subdivisions), since a short typo'd word shares too few trigrams with its record; the candidates are scored by the best `token_sort_ratio` match of any name or alias against a span of the query (replacing `WRatio`), or plain `ratio` where a typo reorders a multi-word name's sorted words, reduced by the weighted share of the rest of the query missing from the record's context, taking whichever name and span score best overall. Name fields now live in the registries instead of the shipped `search_fields.tsv`. Search accuracy (top 10 / top result) and median latency, measured on Latin-script queries (the benchmark no longer mangles non-Latin aliases with Latin letters): countries 90.9% / 83.0% → 100.0% / 99.3%, 3.3ms → 1.8ms; subdivisions 90.3% / 75.6% → 97.0% / 85.1%, 5.8ms → 3.0ms; cities 99.1% / 91.2% → 98.7% / 91.5%, 34.7ms → 6.0ms
- Registries create a record's view when it's accessed instead of keeping one view object, dict entry and int key per record: cities' dataset memory 56.0MB → 24.5MB and subdivisions' 20.9MB → 13.9MB, loading 79ms and 22ms faster
- Filter indexes keep a value held by a single record as a plain int instead of an array, and pack shared values at their exact size: cities' filter index 56.4MB → 41.4MB and subdivisions' 18.4MB → 11.7MB. With on-demand views, a full cache dropped from 206.9MB to 146.6MB
- Memory figures in the README and docs are measured with `tracemalloc` instead of the change in resident memory around each load, which undercounted components loaded after others (the cities lookup index read 4KB)

### Fixed
- The `ingest`, `analysis`, `test` and `test-watch` console scripts were installed with the package, but pointed at development code it doesn't ship, so they failed for anyone who installed localis; they're no longer installed
- Registries weren't safe to share across threads: `search()` kept the query on the shared index, so concurrent searches could read each other's, and threads reaching a cold registry together could each build its dataset or indexes. The query is now local to each search, and datasets and indexes are built under a per-registry lock. `set_population_threshold()` and `set_include_historic()` change shared state and are documented as configuration to set before a registry is shared
- `Country.name` and `Country.official_name` contradicted ISO 3166-1, the documented authority. They had been overridden for 22 countries, and for 14 of them ISO's own name existed nowhere in the record, so a country couldn't be found by its ISO name (e.g. "Korea, Republic of"); Taiwan's ISO official name "Taiwan, Province of China" had been replaced with "Republic of China". They now ship exactly as published, and `official_name` is `str | None` (`None` where ISO gives none). Names in common use moved to the new `Country.common_name` (Debian iso-codes' common name: "South Korea", "Iran", "Taiwan") or remain findable as GeoNames and Wikidata aliases ("Republic of the Congo"); the hard-coded curated alias list is no longer merged, so every country alias now comes from a named source, and search and filters, including the `country` filter on subdivisions and cities, match all three name fields
- Country aliases were never deduplicated or trimmed: the curated list, GeoNames and Wikidata re-added the same names (16 countries had duplicates, such as Zaire, DR Congo and Burma twice) and 2 kept trailing spaces. Country and subdivision aliases now share one normalizer that keeps one alias per name, comparing names by a key that ignores accents, case, punctuation, abbreviations such as "St."/"Saint", "Rep."/"Republic" and "Is."/"Islands", "&"/"and", and filler words, keeping the fullest written form of each and dropping variants of the record's own names (Saint Barthélemy had about 20 spellings of a handful of names). Each country's curated aliases are also copied, so merges no longer append into the module-level alias table
- An exact name match could rank below unrelated results: search averaged weaker alias matches into a record's score, so "German Democratic Republic" scored 0.833 for its own name, below 15 countries scoring 0.855 on "Republic" in their official names
- Search returned nothing for queries of one or two trigrams when they matched more than 2,000 records ("Rio")
- The `country` filter on subdivisions never matched an ISO numeric code given as an int (`subdivisions.filter(country=76)`): ISO 3166-1 numerics were indexed as zero-padded strings ("076") while `Country.numeric` is an int

## [2.0.0] - 2026-10-02

### Breaking
- `City.admin1`/`City.admin2` removed; use `City.subdivisions`, ordered by `admin_level`
- `SubdivisionBase` has a new required `admin_level` field
- Historic (ISO 3166-3) countries are excluded from `filter()`/`search()`/iteration unless `include_historic` is set, and `lookup()` resolves them only by `alpha_4`
- `Country.aliases` and `Subdivision.aliases` are `tuple[str, ...]` instead of `list[str]`: returned entities shared their alias lists with the registry cache, so mutating one changed every later result and what search scored

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
- City coordinates were stored as 32-bit floats, so `City.lat`/`lng` came back with float noise (40.714271545410156 for 40.71427); they're now 64-bit, exactly as shipped
- Registry iteration is lazy again, yielding one entity at a time instead of building the full list (235k entities for cities) up front
- `countries.lookup()` and `subdivisions.lookup()` docstrings claimed to accept the localis id; integers passed to `countries.lookup()` are ISO numeric codes, and ids go through `.get()`
- An ISO code contesting an ambiguous GeoNames record could still be auto-merged into a different record it also qualified for, leaving it both merged and an `ambiguity` orphan: the hard gate blocked on a resolved code and the skill was handed a stale orphan. An ISO code in a namesake collision is now excluded from assignment and always goes to review, so a weaker look-alike can't claim it unreviewed
- `subdivisions.filter(admin_level=1)` always returned nothing: filter index cells are stored as strings and `FilterIndex.get()` only normalized string values, so an integer never matched. Values are now stringified before lookup. The filter index writer also dropped `0` as if it were empty, so the 49 non-administrative groupings had no `admin_level` entry and `admin_level=0` matched nothing
- Subdivision and city ingest skipped whenever their own sources were unchanged, even when an earlier stage had just rebuilt countries (or subdivisions), so their rows could keep stale country ids, subdivision chains and search/filter values. A stage now rebuilds when its sources or any upstream dataset changed. Source manifests were also written at download time, so a run that stopped on orphans (or crashed) marked its sources consumed and the next plain ingest skipped the stage entirely, never applying the skill's decisions; a stage now writes its manifest only after it dumps, and the subdivisions manifest tracks a hash of the map's bypass rules and skill decisions so editing them triggers a rebuild
- City search scored candidates without their state/province: replacing `City.admin1` with `subdivisions` left the shipped `admin1.name`/`admin1.iso_suffix` search fields resolving to nothing, so those 0.6 weights were silently dropped while the trigram index still used them for candidate selection. `CityView` regains an internal `admin1` (the `City` DTO still exposes only `subdivisions`), a test now requires every shipped search field to resolve on its registry's views, and the benchmark reports top-result accuracy and mean reciprocal rank, since a top-10 hit rate can't see a ranking regression
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
- `search_index.bin.gz` changed bytes on every dump even with identical data (gzip embeds the current time, and its OS header byte differs between Python 3.11 and later versions), which made CI's dataset-change check fire whenever CI and the committing machine ran different Python versions; both are now fixed values. Source manifests are written with a trailing newline, so opening one in an editor no longer changes it
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