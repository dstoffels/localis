# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Reduce localis's shipped package size and runtime memory footprint, primarily driven by the cities dataset.
- Ship comprehensive datasets by default, and let the API narrow them ad hoc (population floors, locales) at query time rather than shipping multiple hard-tiered dataset variants.

## Features
Features currently in development, in priority order:

1. Add `Currency` entity + `Country.currency` (ISO 4217, sourced from iso-codes' `iso_4217.json`, not GeoNames' embedded currency fields, since iso-codes is the authoritative source and already the same upstream `countries` data comes from)
2. Add `Language` entity + `Country.languages` (ISO 639, sourced from iso-codes' `iso_639-3.json`, same reasoning as currency; supersedes the old "implement native languages in countries" idea). Currency and Language close the honest gap identified against pycountry (which also covers ISO 4217/639), so both should ship before that comparison gets used as marketing material.
3. Add standalone `Script` reference table (ISO 15924, code → name only). Lowest priority of this batch: a language can be written in more than one script, so it isn't 1:1 with `Language` or `Country`; mostly used for font rendering and BCP-47 locale tags, not something to wire into other entities.

Blocked on the above, needs a dedicated design pass before implementation starts (see Localization section below for the open questions):
- Gettext-based name translation across `Country`/`Subdivision` (and `Currency`/`Language`/`Script` once they exist), including `language_code` support on `filter()`/`search()`.

## Backlog
- Move dev commands (`ingest`, `analysis`, `test`, `test-watch`) out of `[project.scripts]`, which ships in the published package and installs them for every PyPI user even though they point at code the package doesn't include (`ingest/`, `tests/`, dev dependencies), so they crash. A task runner such as poethepoet (`[tool.poe.tasks]`) keeps them dev-only.
- City radius feature using lat/lng to return nearby cities within a specified distance?
- Add filter() kwarg error handling for invalid arguments
- Implement custom exceptions (localis.exceptions module)?
- Thread safety across the package: lazy cache/index loading races on first access, and `SearchIndex.search()` stores per-query state (`query`, `query_token_count`, `match_counts`, `trigram_count`) on the shared instance, so concurrent searches on one registry corrupt each other mid-scoring. Search state should live in locals passed to the helpers, plus locking around lazy loads. Documented as a known issue in the README for v2.
- Implement autocomplete for registries and/or global interface.
- No ISO source maps countries to their language(s) (639 and 3166 don't cross-reference); evaluate Unicode CLDR's territory-language data for this.
- Alias search quality: short/foreign-language country aliases (`DPRK`, `Sverige`) are prone to colliding with unrelated countries once mangled, since countries' search bypasses trigram pre-filtering below 300 records; separately, `normalize()`'s `unidecode` transliteration of non-Latin aliases (Korean, Arabic) doesn't consistently match the same entity's own Latin name, so an exact alias query can miss entirely. Found via `tests/analysis/benchmarks.py`'s alias coverage; tabled as search-engine tuning, not urgent. A third cause underlies both: `SearchIndex._score_candidate()` returns 0 when the primary name scores under the noise threshold, before any alias is scored, and secondary fields (aliases included) are only scored for multi-token queries, so an alias can never rescue a candidate whose name doesn't match ("Golden State" can't find California, "Sverige" can't find Sweden).

## Localization (gettext-based name translation)

Initial plan, not yet started. Goal: pycountry-style translation of `Country`/`Subdivision` names (and `Currency`/`Language`/`Script` once those exist) into other locales via gettext, available both as a per-object transform and as a query-time option on the registries.

### Mechanism

Dependency: none. `gettext` is part of Python's standard library. The actual scope is data: iso-codes ships `.po`/`.mo` locale catalogs per domain (`iso3166-1`, `iso3166-2`, `iso4217`, `iso639-3`, `iso15924`), the same upstream project `countries`/`subdivisions` already source their base data from. Fetching and shipping those as package data (same category as `src/localis/data/*.tsv`) plus a small ingestion step is the actual work. Locale coverage varies a lot per language; gettext's own fallback (an untranslated msgid returns the original English string unchanged) means sparse locales degrade gracefully with no extra error handling needed.

### API shape

`Country.translate(locale: str) -> Country` (`.localize()` also reads fine; `.translate()` matches gettext's own vocabulary) returns a new DTO with `name`/`official_name` swapped to the localized string; `alpha2`/`alpha3`/`numeric`/`flag` stay untouched since codes don't translate. Same shape for `Subdivision.name`, and later `Currency`/`Language`/`Script` names. Out of scope: `aliases` (a separate, already-existing mechanism for colloquial/historical name variants, not systematic per-locale translation) and city names (GeoNames-sourced, no ISO/iso-codes backing; GeoNames has its own, much larger alternate-names-by-language file, a distinct future item). Catalogs load lazily and cache per `(domain, locale)`, the same `@cached_property` pattern `Registry` already uses for its indexes, so an unused locale costs nothing.

### Registry-level `language_code` support

`filter()` and `search()` accept an optional `language_code` kwarg; query mechanics differ between the two.

`filter()` is an exact match against `FilterIndex`, so a localized query reverse-translates cleanly: invert the target locale's gettext catalog into `{normalized_translated_string: english_canonical}`, resolve the localized `name` argument through it, run the existing English `FilterIndex.get()`, then translate the result DTOs back to the requested locale before returning.

`search()` cannot use the same reverse-translation step, since the reverse map is an exact-string lookup and a typo in the localized query (e.g. "Deutschlnd") has no catalog entry to resolve, which would defeat the fuzzy-match tolerance `search()` exists for. Instead, `search()` fuzzy-matches directly against a per-locale corpus built from the localized name strings themselves, then resolves the winning match to its canonical id. Countries (250 active entities) already skip trigram pre-filtering under 300 records, so a per-locale corpus is cheap there; subdivisions (51k) are the same cost class as the existing ~3ms English search and should be built lazily per `(domain, locale)` rather than precomputed and shipped for every locale upfront. Cities have no ISO/iso-codes source and stay out of scope, so this never needs to scale to city-sized data.

`lookup()` matches on language-independent identifiers (`alpha2`, `alpha3`, `iso_code`, etc.), so it has no reverse-translation need; a `language_code` there would only mean "translate the returned DTO," equivalent to `.get(...).translate(locale)`.

### Open questions

- Which locales to ship: all of iso-codes' catalogs, or a curated subset. Leaning all, since gettext's fallback makes sparse coverage safe by default.
- Whether iso-codes' catalogs cover secondary fields (e.g. `Subdivision.type`) or only the primary name/official_name fields, not yet verified.
- Semantics of a cross-registry filter kwarg under `language_code`, e.g. `subdivisions.filter(country="Deutschland", language_code="de")`, where `country` references a different registry's translatable field.
- Actual size of the compiled `.mo` catalogs across all locales isn't confirmed yet, needs measuring before deciding to ship all of them.
- Reconsider Unicode CLDR as the translation data source instead of iso-codes' gettext catalogs; CLDR is more actively maintained and broader-coverage for exactly this kind of translated display-name data. Decide before implementation starts, not after.
## Skill decision lifecycle

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

`retired_decisions: dict[str, RetiredDecision]`, where `RetiredDecision` carries the full `SkillDecision` plus `retired_because: Literal["removed_from_iso", "bypassed"]`. No timestamp, to keep ingest output deterministic. Retirement is one-way: if ISO later restores a retired code, it comes back as a normal orphan, and its retired entry stays as the record of the earlier decision; the skill sees that entry as `previous_decision` in `next` so the history informs the new decision without deciding it. MH-L's decision, removed by hand when the Marshall Islands chains were bypassed, is backfilled as the first entry.

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
