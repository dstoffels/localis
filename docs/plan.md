# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Keep localis's shipped package size and runtime memory footprint in check, primarily driven by the cities dataset. Runtime memory has reached the floor for the current data model, after on-demand views and single-id filter postings (current figures in dev.md's Memory footprint and the README's Performance section); the remaining lever is package size, through splitting cities from the core package (backlog), when adoption calls for it.
- Ship comprehensive datasets by default, and let the API narrow them ad hoc (population floors) at query time rather than shipping multiple hard-tiered dataset variants.

## Features

Next: the Skill decision lifecycle (below), landing before the 1 November 2026 cron. It's pipeline work rather than public API, so it can ship in a 3.0 beta, before the betas move to release candidate (two weeks after b2 at the earliest, since b2's continents restart the clock), since only fixes land in a release candidate.

At 3.0.0 final: set pyproject's classifier back to `Development Status :: 5 - Production/Stable`, and the README's Installation line back to `pip install localis` with its beta banner removed.

Continents, for 3.0.0b2, proposal: `Country.continent`, a nested `Continent` (`name`, `geonames_code`, `geonames_id`), and `countries.filter(continent=...)` matching its name or GeoNames code, for the seven continents taught in schools. A continent is basic information about a country, reachable only through countries: no registry, no lookup, and no tie to macroregions. No authority defines the seven: UN M49 has five regions with the Americas as one, UNSD's current table has South America (`005`) but no North America (`003` is a CLDR grouping only), and it places Antarctica (`010`) in none. So GeoNames is the source, as it is for the other fields it enriches countries with: its `readme.txt` publishes the seven codes with their names and geonameIds (`AF : Africa geonameId=6255146` through `AN : Antarctica geonameId=6255152`), and the `Continent` column of `countryInfo.txt`, which the countries stage already downloads, places each country (Antarctica in `AN`). Ingest checks the table has exactly seven entries and covers every code `countryInfo.txt` uses, and can cross-check names and IDs against the seven `CONT` features in `no-country.zip` (268 KB); any mismatch fails the run. GeoNames' codes are its own convention, not ISO alpha-2s. Countries without a `countryInfo.txt` row get no continent. Continents and macroregions are separate concepts from separate sources and their memberships differ: GeoNames puts Cyprus in Europe where M49 and CLDR place it in Western Asia, which methodology.md states. Rejected: deriving continents from CLDR's containment, since no source there defines seven and CLDR files Antarctica under Outlying Oceania and so Oceania; an `is_continent` flag on macroregions, since Antarctica has no CLDR record to flag and a flagged record would carry M49's membership and GeoNames' at once; a hand-written mapping, which would be localis's own judgment; and a `continents` registry, unneeded since every continent has a member country. Docs: the README's countries filter row and a sentence declaring continents GeoNames enrichment, separate from macroregions despite the overlap, a CHANGELOG Added entry and the methodology section; tests extend the shared filter tables (`_country_values`). It's an API addition, so b2 restarts the two weeks before the release candidate.

Cities search, bug for 3.0.0b2: results with equal scores are ordered by their trigram score, which says little about which one a query means, so `cities.search("New York")` ranks East New York first, tied at 0.76 with New York City (8.8 million) and West New York. It's the one problem localis's known adopter reported (PR #8, April 2026): "Paris" resolving to Paris, Texas rather than France. In 3.0.0b1, Paris, Ontario (12,000) ranks first and Paris, France (2.1 million) third, all at 1.0; "Rome" puts a US town of 1,019 above Rome, Italy, and "Florence" leaves Italy out of the top three. The fix is population as the tie-breaker for cities, ahead of the trigram score: each registry names one `PROMINENCE_COLUMN`, a numeric store column named as in an ordering (`"-populations"` for cities, larger first; none for the rest), which `SearchIndex` reads from the store by row, at no load cost. Prominence applies at all three cuts, not only the final sort: the stage 1 shortlist (200) and stage 2 candidates (50) pick among records tied at the cut by prominence, since a name shared by more than 50 places (San Antonio, Santa María) could otherwise lose its largest before stage 3. Implemented (#26). Subdivisions have no prominence: `admin_levels` was tried and lowered top-1 from 93.9% to 93.5% (failures 135 to 145), most likely because so few distinct values only favour level 1 among the records tied at the cuts. A population key, the total population of each subdivision's shipped cities, was measured and set aside: of 2,464 names shared by two or more subdivisions, `admin_level` separates 493, and 1,971 tie at the same level (mostly US counties, such as 30 Washington Counties), but a bare county name is genuinely ambiguous and subdivision queries usually carry context. It would need cities loaded before subdivisions are dumped, or a sidecar file, so it waits for a real need, as does a tuple of prominence columns. Only results that already score the same are reordered, so it changes no API and doesn't restart the beta's clock; rerun `poe analysis` to confirm accuracy holds. Population as the whole order was rejected, since it overrides relevance (it puts Springfield, Missouri and Springfield, Massachusetts ahead of the Springfield, Illinois a query's context names), which is what the opt-in `population_sort=True` is for. Near-ties, a slightly better match for a much smaller city, would need population blended into the score itself, which can let a large city outrank a better-matching small one; measure first how often the benchmark's intended city comes second by a small margin.

Ingest, bug for 3.0.0b2: `_main_commit()` looks up cldr-json's head commit through the GitHub REST API without a token, and the unauthenticated limit of 60 requests an hour counts per IP, which GitHub-hosted runners share with other jobs, so the Test workflow's ingest failed on 5 October 2026 with a 403 "rate limit exceeded" that `_retrying()` doesn't retry. The fix: `cldr_url()` passes the `GITHUB_TOKEN` environment variable to `_main_commit()`, which sends it as an unredirected `Authorization` header (`add_unredirected_header()`, so a redirect never carries it to another host), and the ingest steps in `test.yaml` and `ingest.yaml` pass `GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}`. The token is scoped by call site rather than by inspecting URLs, so iso-codes' Salsa lookup never sees it. Implemented (#27); the `download.py` change has to reach the `ingest` branch and the `ingest.yaml` change `main` before the 1 November cron, in either order, since each half works without the other. Both jobs hold only `contents: read`, so no write token reaches project code, and local runs stay unauthenticated. Reading the head from git's `info/refs` endpoint was rejected: it needs no token, but trades the documented API shared with Salsa's lookup for a pkt-line parser.

Cities search, potential feature: GeoNames names New York City "New York City", so `cities.filter(name="New York")` finds nothing and search finds it only partly. English alternate names for cities, previously left out because adding all of them would bloat the dataset, could be bounded instead: English only, for cities above a population floor (15,000 keeps about 34,000 of 236,000), skipping colloquial and historic entries as the subdivision stage does. `alternateNamesV2.txt` is already fetched for subdivisions, so it needs no new source. Measure the growth of the shipped data and the canon trigram index before deciding; a `City.aliases` field would be an API addition, so in a beta it restarts the two weeks before the release candidate. Names in other languages belong to the translation layer (Translations, below), not to `City.aliases`.

## Done

- Currency, Script and Language (ISO 4217, ISO 15924, ISO 639-3), implemented 2026-10-04 for 2.2.0, closing the gap against pycountry, which also covers those standards. methodology.md describes their sources and rules.
- Atomic pipeline, implemented 2026-10-04 from the review of codebase area 1: every stage builds on every run into staging, and a build is promoted only whole and reconciled. dev.md's Pipeline section describes it.
- One CLDR and one iso-codes commit per run, so every stage builds from the same upstream versions, done in the review of codebase area 3.

## Backlog

1. Batch throughput for large cleanups: registries are thread-safe, but on the standard (GIL) build threads don't parallelize search, which is mostly Python code, and rapidfuzz's single scorer calls don't release the GIL usefully (only `process.cdist(..., workers=N)` does, which doesn't fit localis's search). Free-threaded Python is the threaded route: rapidfuzz supports 3.14t since 3.14.2 (3.14.0 added support, 3.14.6 dropped the experimental 3.13t wheels). It requires no change to `requires-python = ">=3.11"`, since free threading is a property of the user's interpreter and localis is pure Python; GIL builds keep working as now. Adopting it is additive: a 3.14t job in the test matrix, optionally raising the `rapidfuzz` floor to 3.14.2 and adding the free-threading PyPI classifier, and a batch API such as `search_many(queries, workers=N)` on a thread pool (parallel on 3.14t, serial on GIL builds, with process pools as the GIL-build option: each worker loads its own cache, about 127MB for cities). Measure throughput on both builds.
2. City radius feature using lat/lng to return nearby cities within a specified distance?
3. Implement autocomplete for registries and/or global interface.
4. Search, remaining limits: a subdivision query without context can't pick among same-name records (dozens of Washington Counties), which caps subdivisions' top-result accuracy; benchmarking subdivision queries with their country as context would measure that case the way cities' admin1 context does. Indexing each name separately (true per-name Dice) is parked until a failure trace shows alias dilution.
5. Macroregion filters on subdivisions and cities (`cities.filter(macroregion="Europe")`), at the cost of another filter column on the largest dataset; deferred until there's demand. The macroregions design is recorded in `methodology.md` (sources, naming, placement rules) and `dev.md`.
6. Split cities from the core package (`localis` with macroregions, countries and subdivisions, about 11MB installed; cities as an extra backed by a separate data package, about 42MB). Deferred until users report package size as a problem. City rows store country and subdivision ids that are only valid against the exact core data they were built with, so the two would release in lockstep from one ingest run with an exact-version pin, which removes most of the usual benefit of a split.
7. Population range filters on cities, `cities.filter(population__gt=..., population__lt=...)`, removed as a commented-out stub from `CityRegistry.filter()` during the code review cleanup. The filter index only holds exact values, so a range needs its own path, such as a scan over `CityStore.populations` or a population-sorted id array searched with `bisect`.
8. Corroboration for `wikidata_changed` orphans: accepting a changed crosswalk mapping when automerge's scoring would pick the same record. Left out so every relink of a shipped subdivision is reviewed; revisit if those orphans turn out to be mostly noise.
9. Measure the full pipeline's local run time, never measured since the atomic pipeline landed.
10. Evaluate replacing GeoNames with more authoritative, versioned sources, source by source. No authoritative global city dataset exists: UN/LOCODE (UNECE) is a UN standard released twice a year with ISO 3166-2 subdivision codes, but it lists trade and transport locations rather than all populated places and has no population, which search's tie-breaker and `population_sort` need; Natural Earth's populated places (about 7,000) are too few; Wikidata is crowd-edited; national gazetteers are authoritative but come in hundreds of formats. For subdivisions below ISO 3166-2, geoBoundaries (CC BY 4.0, versioned GitHub releases, built from government sources where available) is the strongest candidate; measure its download size, coverage and per-country licensing. Countries' GeoNames fields have statistical replacements (UN World Population Prospects, World Bank). City keys are GeoNames IDs, so replacing GeoNames for cities, or for any subdivision keyed by it, changes keys and is a 4.0 change rather than one to fit before the 3.0 release candidate.
11. Gzip every shipped data file. 3.0.0b1's wheel is 24.7 MB and installs to 53.6 MB, cities 42.0 MB of it; the `.bin.gz` indexes are already gzipped, but the plain-text files are 31.9 MB installed (`cities.tsv` 13.3 MB, cities' `filter_index_offsets.tsv` 7.7 MB, `lookup_index_int.tsv` 3.4 MB, `subdivisions.tsv` 3.1 MB) and gzip to about 10.4 MB at level 9, so the install drops to about 32 MB. The wheel barely changes, since zip already deflates them. Every data file is read whole with `open()` (views, `LookupIndex`, the inverted indexes' offsets rows), none by seeking, so gzip breaks no access pattern, and decompression is negligible against the full cache's ~1.2s load. Compress all of them, not only the large ones, so `data/` holds one format instead of `.tsv` beside `.gz`; `NOTICE` stays plain text, since it's the attribution redistributors must keep readable. Ingest writes them with `mtime=0`, as `ingest/utils/index.py` already does for the postings, so output stays deterministic and the drift check holds; the loaders share one `gzip.open(..., "rt")` helper. No API change, so it can land in any release. Follow-ups to measure after: the offsets files are numbers stored as text and would be several times smaller as packed binary arrays, and cities' `lookup_index_int.tsv` (GeoNames id to row) may be rebuildable at load from the `geonames_id` column rather than shipped.

## Skill decision lifecycle

Status: implemented (#28), to reach `dev` before the next scheduled ingest run (the monthly cron, 1 November 2026, which merges `dev` into `ingest` first), the first run that can retire or reopen skill decisions. The first local `poe ingest` baselines `candidates_seen` and rewrites `resolution_map.json`, which has to be committed with it.

Goal: a skill decision is never silently ignored or replaced. Wikidata merges, automerge, `geonames_absent` and the non-administrative bypass are recomputed every run and already follow source updates. Skill decisions are permanent and applied first, and today only `flag_wikidata_conflicts()` ever re-examines them, so a GeoNames or ISO update can leave one wrong without anything failing.

### Gaps being closed

1. An add is never re-checked against new GeoNames records. When GeoNames adds the missing place (a too-new district like Kassanda, a gap like Karuzi), it ships twice unless Wikidata happens to link the new record.
2. A merge whose target was deleted, or is claimed by another decision, falls through to Wikidata and automerge with only a WARN line, so a fuzzy match can replace a reviewed decision unreviewed.
3. Decisions for ISO codes that were removed, renumbered or newly bypassed stay in the map. `flag_wikidata_conflicts()` iterates the decisions, not the live codes, so one still mapped by Wikidata could be sent to the skill, which can't load the subdivision.

Out of scope: re-checking a merge against a better record GeoNames adds later. It's rare and doesn't create a duplicate; Wikidata already catches the linked cases.

### Classification

Every decision is classified on every run:

- **applied**: target present and unclaimed, or an add with no new qualifying candidate. Nothing changes.
- **stale**: a merge whose GeoNames record no longer exists.
- **contested**: two or more decisions name the same record. All of them go to review and none is applied, so dictionary order never picks a winner.
- **new_candidate**: an add for which a GeoNames record now qualifies that didn't when the decision was made.
- **retired**: the ISO code is no longer in ISO's data, or is now bypassed as non-administrative. The decision moves from `skill_decisions` to a new top-level `retired_decisions` map, so the pipeline documents its own history rather than relying on git.

stale, contested and new_candidate become orphans in three new buckets, so the run exits 10 exactly like a `wikidata_conflict`. Each bucket gets its own dataclass in `resolution_map.py`, following `WikidataConflictOrphan`: `StaleDecisionOrphan(iso_code, decision_geonames_id)`, `ContestedDecisionOrphan(iso_code, decision_geonames_id, contested_with: list[str])`, `NewCandidateOrphan(iso_code, candidate_geonames_ids: list[int])`. `Orphans.count()`/`summary()` include them.

### Pipeline changes

`apply_skill_decisions()` does the classification before applying anything: it retires decisions for codes that are gone or bypassed, builds a target-to-codes map to find contested ones, checks each merge target's existence, and applies only the rest. stale and contested codes are written to their buckets and **not** returned as remaining, so neither Wikidata nor automerge can take them. It resets its two buckets itself, since `try_merge()` only resets its own.

`flag_wikidata_conflicts()` iterates live decisions only, never retired ones.

### `retired_decisions`

`retired_decisions: dict[str, RetiredDecision]`, where `RetiredDecision` carries the full `SkillDecision` plus `retired_because: Literal["removed_from_iso", "bypassed"]`. No timestamp, to keep ingest output deterministic. Retirement is one-way: if ISO later restores a retired code, it comes back as a normal orphan, and its retired entry stays as the record of the earlier decision; the skill sees that entry as `previous_decision` in `next_orphan` so the history informs the new decision without deciding it. MH-L's decision, removed by hand when the Marshall Islands chains were bypassed, is backfilled as the first entry.

A new `flag_new_candidates()` runs after `try_merge()`, once every recomputed source has claimed what it will, so only genuinely unclaimed records count. For each add decision it scores the ISO subdivision against its country's unclaimed GeoNames records at every level, with automerge's gates (`score_candidates()` with the type-family and directional checks on, `score >= threshold`). A level-crossing match only reopens a decision for review, never merges, so the wider pool is safe here even though automerge itself stays same-level. A qualifying record not in the decision's `candidates_seen` makes it a `new_candidate` orphan.

### `candidates_seen`

Without it the check would reopen the same decisions every run: Szolnok scores high against Szolnoki Járás, which the skill already rejected. `SkillDecision` gains `candidates_seen: list[int] | None`, the qualifying records at the time of the decision, mirroring how `wikidata_seen` makes a Wikidata override a known one. The skill's `write_resolution()` computes it with the same function `flag_new_candidates()` uses, for adds only (empty for merges). A decision with `None` gets its current qualifying records stored as its baseline on the first run instead of being reopened, which migrates the existing adds without a one-off script; every one of them was decided with its full candidate list in view.

### Skill side

`get_next_orphan()` includes `current_decision` (id or "add as-is", and its reason) for all three new buckets, as for `wikidata_conflict`. First batches via `_flagged_candidates()`: the new qualifying records noted "new GeoNames record since this decision" for new_candidate; the contested record noted "also named by <codes>" for contested; Wikidata's valid mapping, if any, noted "Wikidata's mapping" for stale, otherwise the regular top tier. `pop_orphan()` handles the new buckets. `SKILL.md` gains a short section like the `wikidata_conflict` one: keep the current decision only with a concrete reason, and escalate any reopened decision a human made, since the agent shouldn't overturn a human ruling on its own.

### Docs

`methodology.md`: the precedence section states the guarantee and the five classes; Known limitations drops the duplicate risk for adds. `dev.md`: the pipeline integration steps and the new buckets. CHANGELOG entry.

### Decisions

- `contested` keeps its own bucket. It should only arise from manual map edits or a decision made against stale state, but when it does, the note has to say exactly why the decision was reopened.
- A place too new for GeoNames still requires human review, even though adds become recoverable. The agent escalates; the pipeline falls back to review rather than ever adding on the agent's own judgment. `SKILL.md` Step 5 is unchanged.
- Retired decisions are kept in the map, never deleted, so the pipeline is self-documenting.

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

Goal: every shipped subdivision resolution is independently verified, and the audit is idempotent, so running it twice against the same data changes nothing and a finished audit stays finished until the facts behind a verdict change. Required before the audit claims in `methodology.md` can say more than "spot-checked by sampling". Designed together with the skill decision lifecycle above, since both rely on fingerprints and on history that is moved rather than deleted.

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
- **Adds**: verified by the lifecycle plan's `new_candidate` check finding no qualifying record.
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
