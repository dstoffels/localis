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
- City radius feature using lat/lng to return nearby cities within a specified distance?
- Add filter() kwarg error handling for invalid arguments
- Implement custom exceptions (localis.exceptions module)?
- Set thread locks for concurrent access to registries
- Implement autocomplete for registries and/or global interface.
- Redevelop Wikidata SPARQL query and parsing logic for country alias enrichment.
- No ISO source maps countries to their language(s) (639 and 3166 don't cross-reference); evaluate Unicode CLDR's territory-language data for this.
- Alias search quality: short/foreign-language country aliases (`DPRK`, `Sverige`) are prone to colliding with unrelated countries once mangled, since countries' search bypasses trigram pre-filtering below 300 records; separately, `normalize()`'s `unidecode` transliteration of non-Latin aliases (Korean, Arabic) doesn't consistently match the same entity's own Latin name, so an exact alias query can miss entirely. Found via `tests/analysis/benchmarks.py`'s alias coverage; tabled as search-engine tuning, not urgent.

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