# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Keep localis's shipped package size and runtime memory footprint in check, primarily driven by the cities dataset. Runtime memory has reached the floor for the current data model, after on-demand views and single-id filter postings (current figures in dev.md's Memory footprint and the README's Performance section); the remaining lever is package size, through splitting cities from the core package (backlog), when adoption calls for it.
- Ship comprehensive datasets by default, and let the API narrow them ad hoc (population floors) at query time rather than shipping multiple hard-tiered dataset variants.

## Features

Next: release 3.0.0b2. The betas move to release candidate two weeks after b2 at the earliest, since b2's continents add API and restart the clock, and only fixes land in a release candidate.

At 3.0.0 final: set pyproject's classifier back to `Development Status :: 5 - Production/Stable`, and the README's Installation commands back to `pip install localis` and `uv add localis` with its beta banner removed.

Cities search, potential feature: GeoNames names New York City "New York City", so `cities.filter(name="New York")` finds nothing and search finds it only partly. English alternate names for cities, previously left out because adding all of them would bloat the dataset, could be bounded instead: English only, for cities above a population floor (15,000 keeps about 34,000 of 236,000), skipping colloquial and historic entries as the subdivision stage does. `alternateNamesV2.txt` is already fetched for subdivisions, so it needs no new source. Measure the growth of the shipped data and the canon trigram index before deciding; a `City.aliases` field would be an API addition, so in a beta it restarts the two weeks before the release candidate. Names in other languages belong to the translation layer (Translations, below), not to `City.aliases`.

## Done

- Currency, Script and Language (ISO 4217, ISO 15924, ISO 639-3), implemented 2026-10-04 for 2.2.0, closing the gap against pycountry, which also covers those standards. methodology.md describes their sources and rules.
- Atomic pipeline, implemented 2026-10-04 from the review of codebase area 1: every stage builds on every run into staging, and a build is promoted only whole and reconciled. dev.md's Pipeline section describes it.
- One CLDR and one iso-codes commit per run, so every stage builds from the same upstream versions, done in the review of codebase area 3.
- Continents (#25), 3.0.0b2: `Country.continent`, a plain `Continent` (`name`, `geonames_code`, `geonames_id`) with no id or key, since there's no registry, and `countries.filter(continent=...)`, from GeoNames' readme and `countryInfo.txt` as enrichment rather than a standard. methodology.md's Continents section records the sourcing and what was rejected.
- Cities search tie-break (#26), 3.0.0b2: cities tied on score rank by population, largest first, at the shortlist and candidate cuts as well as the final sort, through each registry's one `PROMINENCE_COLUMN`. dev.md's search section records it, and why subdivisions have none.
- The cldr-json commit lookup authenticates with the CI job's `GITHUB_TOKEN` (#27), 3.0.0b2, so a shared runner's unauthenticated rate limit no longer fails a run.
- Skill decision lifecycle (#28), 3.0.0b2: every skill decision is classified on every run, stale, contested and new-candidate decisions go back to the skill, and retired ones move to `retired_decisions`. methodology.md's Merge precedence and dev.md describe it.
- Gzipped data files (#29), 3.0.0b2: every shipped data file but `NOTICE` is gzipped, cutting the install from 53.6 MB to about 32 MB. dev.md's shipped-size section describes it.
- Data changelog, 3.0.0b2: every ingest run that changes a record adds a table to the CHANGELOG's Data subsection and its renamed, added and removed records to `DATA_CHANGELOG.md`, replacing the per-stage change reports. dev.md's Pipeline section describes it.

## Backlog

1. Batch throughput for large cleanups: registries are thread-safe, but on the standard (GIL) build threads don't parallelize search, which is mostly Python code, and rapidfuzz's single scorer calls don't release the GIL usefully (only `process.cdist(..., workers=N)` does, which doesn't fit localis's search). Free-threaded Python is the threaded route: rapidfuzz supports 3.14t since 3.14.2 (3.14.0 added support, 3.14.6 dropped the experimental 3.13t wheels). It requires no change to `requires-python = ">=3.11"`, since free threading is a property of the user's interpreter and localis is pure Python; GIL builds keep working as now. Adopting it is additive: a 3.14t job in the test matrix, optionally raising the `rapidfuzz` floor to 3.14.2 and adding the free-threading PyPI classifier, and a batch API such as `search_many(queries, workers=N)` on a thread pool (parallel on 3.14t, serial on GIL builds, with process pools as the GIL-build option: each worker loads its own cache, about 127MB for cities). Measure throughput on both builds.
2. City radius feature using lat/lng to return nearby cities within a specified distance?
3. Implement autocomplete for registries and/or global interface.
4. Search, remaining limits: a subdivision query without context can't pick among same-name records (dozens of Washington Counties), which caps subdivisions' top-result accuracy; benchmarking subdivision queries with their country as context would measure that case the way cities' admin1 context does. Indexing each name separately (true per-name Dice) is parked until a failure trace shows alias dilution. A prominence key for subdivisions, the total population of each one's shipped cities, waits for a real need: a bare county name is genuinely ambiguous, and it would need cities loaded before subdivisions are dumped, or a sidecar file. For cities, near-ties (a slightly better match for a much smaller city) would need population blended into the score itself; measure first how often the benchmark's intended city comes second by a small margin.
5. Macroregion filters on subdivisions and cities (`cities.filter(macroregion="Europe")`), at the cost of another filter column on the largest dataset; deferred until there's demand. The macroregions design is recorded in `methodology.md` (sources, naming, placement rules) and `dev.md`.
6. Split cities from the core package (`localis` with macroregions, countries and subdivisions, about 11MB installed; cities as an extra backed by a separate data package, about 42MB). Deferred until users report package size as a problem. City rows store country and subdivision ids that are only valid against the exact core data they were built with, so the two would release in lockstep from one ingest run with an exact-version pin, which removes most of the usual benefit of a split.
7. Population range filters on cities, `cities.filter(population__gt=..., population__lt=...)`, removed as a commented-out stub from `CityRegistry.filter()` during the code review cleanup. The filter index only holds exact values, so a range needs its own path, such as a scan over `CityStore.populations` or a population-sorted id array searched with `bisect`.
8. Corroboration for `wikidata_changed` orphans: accepting a changed crosswalk mapping when automerge's scoring would pick the same record. Left out so every relink of a shipped subdivision is reviewed; revisit if those orphans turn out to be mostly noise.
9. Measure the full pipeline's local run time, never measured since the atomic pipeline landed.
10. Evaluate replacing GeoNames with more authoritative, versioned sources, source by source. No authoritative global city dataset exists: UN/LOCODE (UNECE) is a UN standard released twice a year with ISO 3166-2 subdivision codes, but it lists trade and transport locations rather than all populated places and has no population, which search's tie-breaker and `population_sort` need; Natural Earth's populated places (about 7,000) are too few; Wikidata is crowd-edited; national gazetteers are authoritative but come in hundreds of formats. For subdivisions below ISO 3166-2, geoBoundaries (CC BY 4.0, versioned GitHub releases, built from government sources where available) is the strongest candidate; measure its download size, coverage and per-country licensing. Countries' GeoNames fields have statistical replacements (UN World Population Prospects, World Bank). City keys are GeoNames IDs, so replacing GeoNames for cities, or for any subdivision keyed by it, changes keys and is a 4.0 change rather than one to fit before the 3.0 release candidate.
11. Smaller data files after gzipping (#29): the offsets files are numbers stored as text and would be several times smaller as packed binary arrays, and cities' `lookup_index_int.tsv.gz` (GeoNames id to row) may be rebuildable at load from the `geonames_id` column rather than shipped. Measure both.

## Translations

Status: designed, not started. It only adds API, so it can land in any 3.x release.

Goal: names in other languages for every record, as a layer on top of the shipped datasets rather than baked into them, so the core data and its indexes stay English plus local names and every translation has a citable source.

### Showing versus matching

Showing a translated name (`country.name_in("de")` returning "Deutschland") only stores strings. Matching one (`lookup("Deutschland")` finding Germany) needs a reverse map, and fuzzy search needs trigram entries on top. The reverse map is free: each locale's table (key to name) is inverted when it loads, so exact lookup and filtering by a translated name reuse the same file. Fuzzy search is the costly part, since it needs a trigram index per locale; it can be built in memory the first time a locale is searched rather than shipped, trading memory and startup for package size. Non-Latin input (Japanese, Russian) needs its own normalization before it can be searched; exact lookup works with it as is.

### Sources

Countries, currencies, languages and scripts take CLDR's localized display names (`cldr-localenames`), keyed by code, from the same pinned CLDR commit as the rest of ingest. CLDR is the standard ICU, browsers and Babel use, and it's already a localis source. Cities and GeoNames subdivisions take names from `alternateNamesV2.txt`, already fetched, keyed by geonameid with a language code per name, skipping colloquial and historic names as the subdivisions stage does. ISO subdivisions take them through their GeoNames counterpart where merged, or from CLDR's subdivision names if cldr-json publishes them, which needs checking. The locale set is CLDR's own coverage level, modern or full (cldr-json ships both as `-modern` and `-full` packages), so the choice cites CLDR rather than a list localis keeps; which one depends on measured size. Variants fall back to their parent locale (`de_AT` to `de`) by CLDR's `parentLocales`.

### Local names stay in the baseline

The shipped aliases keep English plus local names, the Latin-script names in a territory's own languages that subdivisions already carry ("Bayern" for Bavaria). Local names are what turns up in real-world input such as addresses, so they stay matchable without choosing a locale. Only names in other languages ("Frankreich" for France) move to the translation layer.

### API

A locale-bound object, `de = localis.locale("de")`, exposes the registries: `de.countries.lookup("Deutschland")` maps the translated name to the record's key, not to its English name (English names aren't unique and change), and returns the entity. Entities stay canonical, so a record looks the same however it was fetched; translations come from `name_in(locale)` on entities or a `localized_name` on the locale-bound view. No global "current locale" setting, since it would leak between threads and between libraries in one process.

### Packaging

One table per locale per dataset (key to name), loaded the first time that locale is used. Keys are stable references (`alpha2`, currency and language codes, `geonames_id`), not internal ids, so a separate data package (`pip install localis[names]`) wouldn't need to release in lockstep with the core the way a cities split would; a key it doesn't have returns no translation.

### Open questions

- A missing translation returns None or falls back to English. Leaning towards fallback, not decided; None tells the caller the translation is missing, and `name_in("de") or name` gives the fallback in one expression.
- Modern or full locale coverage, and translations in the core package or a separate one, both decided by measured size.
- Whether fuzzy search over translated names is in the first release or exact lookup and filtering ship first, and how non-Latin input is normalized.
- `name_in()`, `localized_name` or both.
- Whether cldr-json publishes subdivision names.

### Rejected

- iso-codes' gettext catalogs (pycountry's approach): keyed by the English name, so a renamed record loses its translations, and volunteer-translated where CLDR is the standard and already a source.
- Translating an entity's fields in place: a record's `name` would depend on how it was fetched.
- A locale list localis picks itself, rather than CLDR's coverage levels.
- Moving local names out of the baseline: it would shrink the data little and make English-default matching worse on the input localis is used to clean.

## Audit system

Goal: every shipped subdivision resolution is independently verified, and the audit is idempotent, so running it twice against the same data changes nothing and a finished audit stays finished until the facts behind a verdict change. Required before the audit claims in `methodology.md` can say more than "spot-checked by sampling". Designed together with the skill decision lifecycle (#28), since both rely on fingerprints and on history that is moved rather than deleted.

### Idempotency rules

1. **The queue is derived, never stored.** Each run computes what needs auditing from the map and the source data. No progress cursor or "audited so far" counter exists; a resolution is audited if and only if it has a current verdict.
2. **A verdict is bound to a fingerprint.** It holds only for the facts it was made against: the ISO entry (code, name, type, parent) and the GeoNames record (id, name, admin code, level). Any change to either reopens it; comparing ids alone would let a GeoNames rename under the same id keep a stale verdict.
3. **Nothing is overwritten or deleted.** A verdict whose fingerprint no longer matches moves to `audit_history` with the reason, like `retired_decisions`. The earlier `audited` record and its `reconcile()`, which deleted an entry a fresh result contradicted and was never populated, were removed ahead of this design.

### Verification tiers

Cheapest first; a resolution only moves to the next tier if the previous one can't verify it.

1. **Corroboration.** Two independent methods agree: a Wikidata merge that automerge's scoring would also make. Computed every run from the data alone, at no cost. This tier can only ever verify Wikidata merges: Wikidata runs first and takes every code it can validly map, so automerge and the skill only see codes with no valid Wikidata mapping, and their results have nothing to be corroborated against (the first audit confirmed 0 of 523). Most of the dataset still verifies here, since Wikidata resolves about 4,300 of 5,046 codes.
2. **Blind re-derivation.** The skill resolves the subdivision again without seeing the existing decision. Agreement verifies it; disagreement escalates. Independence comes from not anchoring on the earlier answer.
3. **Human adjudication.** Only disagreements from tier 2 and whatever the agent escalates.

### Scope by source

- **Automerge**: every result goes to blind re-derivation, since none can be corroborated, lowest margin first, since that's where `MG-D` and `TW-TNN` sat.
- **Wikidata**: single-source merges automerge wouldn't make. Turns its >99% agreement rate into a per-entry record.
- **Skill decisions**: agent decisions go through blind re-derivation; human decisions are spot-checked rather than re-derived.
- **Adds**: verified by the skill decision lifecycle's `new_candidate` check finding no qualifying record.
- **Non-administrative bypass**: audited per rule, not per entry. Each `NON_ADMINISTRATIVE_TYPES` entry carries its evidence (source URL and the quoted statement of no administrative function), so an unsourced ruling like the earlier Guinea-Bissau exclusion can't recur.
- **Missed matches**: a duplicate scan pairing ISO-only records with unclaimed GeoNames-only records in the same country by name similarity. The only way to audit the unmerged list, which no per-resolution check reaches.

### Plumbing

Each verdict is an `AuditEntry` of `{id, fingerprint, verdict, method, auditor, findings}`, where `verdict` is verified, rejected or inconclusive, and `method` is corroboration, blind re-derivation or human. A rejected verdict never fixes anything itself: it becomes an `audit_rejected` orphan, so every correction still flows through `skill_decisions`, the one correction path `methodology.md` already requires (an audit verdict confirms or rejects a result, never overrides it).

Verdicts sit alongside the results they cover; a verified result is still written to `wikidata_merge` or `automerge.resolutions` as usual. The removed `reconcile()` instead skipped writing a result that matched its audited entry, leaving the audit record as the claim's only record, which the skill's `_apply_resolved_claims()` never read, so the target looked unclaimed and could be merged a second time. Any design that stores a claim only in the audit record has to add it to every place claims are reconstructed.

Coverage is reported per source, method and auditor ("N of M automerge results verified, by method") and published in `methodology.md` as a falsifiable claim.

### Auditor model

Blind re-derivation runs on Fable 5.1, a different and more capable model than the decider (Opus 5.5). A weaker auditor's agreement adds little and its disagreements are mostly its own errors, each costing a human adjudication; a fresh run of the same model shares its knowledge gaps, so a confident wrong decision tends to be reproduced and marked verified. Fable is expensive, so cost is bounded by design: verdicts persist until their fingerprint changes, making the audit a one-time cost per entry plus a handful of re-audits per source update; corroboration removes most Wikidata merges before Fable sees anything, but every automerge and skill merge (523 in the first audit) plus the uncorroborated Wikidata merges go to Fable, a large first pass that then shrinks to the entries a source update touches; clear-cut cases settle in the first batch without a web search; human decisions are sampled rather than re-derived. A model from another vendor would be more independent still, since its training gaps are less likely to overlap with Opus's, but would need its own harness outside Claude Code's MCP setup; noted for later.

### Open questions

- Whether corroboration counts as verified on its own, or only lowers the sampling rate: Wikidata and automerge are independent in method but could share a GeoNames naming quirk.
