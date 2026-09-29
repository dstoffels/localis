# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Reduce localis's shipped package size and runtime memory footprint, primarily driven by the cities dataset.

## Features
Features currently in development

~~- Cities search-index and filter-index memory footprint and load time. Search index moved from per-trigram `base64(varint(delta(ids)))` TSV lines to a gzip'd raw fixed-uint32 blob plus a small offsets table, decoded once via `gzip.decompress()` + `array.frombytes()` and sliced per trigram, instead of a serial byte-at-a-time varint decode. Filter index swapped its `defaultdict(list)` postings for `defaultdict(lambda: array("I"))`, no format change needed there. Result: cities' `_search_index` 645MB → 195MB (−70%, 1.57s → 0.30s to build, 5.2x faster), `_filter_index` 109MB → 78MB (−29%, build time effectively unchanged), total package memory across all three registries 1134MB → 587MB (−48%), total load time ~4.3s → ~2.7s. Full benchmarks, the rejected alternatives, and the architecture are documented in `docs/dev.md`'s Performance Profile.~~

## Backlog
- Patch missing flags for countries
- City radius feature using lat/lng to return nearby cities within a specified distance
- Add filter() kwarg error handling for invalid arguments
- Add py.typed marker (PEP 561)
- Implement custom exceptions (localis.exceptions module)?
- Set thread locks for concurrent access to registries
- Implement autocomplete for registries and/or global interface.
- Add `Currency` entity + `Country.currency` (ISO 4217, sourced from iso-codes' `iso_4217.json`, not GeoNames' embedded currency fields, since iso-codes is the authoritative source and already the same upstream `countries` data comes from)
- Add `Language` entity + `Country.languages` (ISO 639, sourced from iso-codes' `iso_639-3.json`, same reasoning as currency; supersedes the old "implement native languages in countries" idea)
- Add standalone `Script` reference table (ISO 15924, code → name only). Low priority: a language can be written in more than one script, so it isn't 1:1 with `Language` or `Country`; mostly used for font rendering and BCP-47 locale tags, not something to wire into other entities.
- Add a separate `HistoricCountry` registry (ISO 3166-3: USSR, Yugoslavia, East Germany, etc.), kept apart from the live `countries` table rather than flattened in, since these entities no longer exist at all (unlike e.g. Kosovo, which is current but diplomatically contested). ISO 3166-3's former-to-successor mapping also isn't reliably 1:1 (some dissolved into several states), so there's no safe automatic redirect into the live table either. Before building it, audit whether cleaner 1:1 renames (Burma → Myanmar-style) are already covered by existing Wikidata aliases on the modern country.
- Split `localis` into a lean core (countries + subdivisions) and a `localis-cities` companion distribution shipping the city dataset, installed via `pip install localis[cities]` extras. Same monorepo, same CI/release pipeline; a wheel can't conditionally include package data by install flag, so two coordinated PyPI distributions is the closest real implementation of a single-repo, opt-in-heavy-data package. Baseline (post memory rework): core would ship ~7.9MB disk / ~80MB peak memory versus the current 98MB disk / 587MB peak memory for the full package (see `docs/dev.md`'s Performance Profile).
- Add a minimum-population floor to `data/cities/scripts/load_cities.py`'s `is_valid_city()` (currently admits any allowed feature code with population > 0). Recommended default: population > 500, cutting the dataset to roughly 186,310 cities (39.4% of the current 472,613). A coverage tradeoff, not a pure size win, revisit the threshold if it drops cities users actually need. See `docs/dev.md`'s Performance Profile for the full population-distribution table.

## Localization (gettext-based name translation)

Initial plan, not yet started. Goal: pycountry-style translation of `Country`/`Subdivision` names (and `Currency`/`Language`/`Script` once those exist) into other locales via gettext, available both as a per-object transform and as a query-time option on the registries.

### Mechanism

Dependency: none. `gettext` is part of Python's standard library. The actual scope is data: iso-codes ships `.po`/`.mo` locale catalogs per domain (`iso3166-1`, `iso3166-2`, `iso4217`, `iso639-3`, `iso15924`), the same upstream project `countries`/`subdivisions` already source their base data from. Fetching and shipping those as package data (same category as `src/localis/data/*.tsv`) plus a small ingestion step is the actual work. Locale coverage varies a lot per language; gettext's own fallback (an untranslated msgid returns the original English string unchanged) means sparse locales degrade gracefully with no extra error handling needed.

### API shape

`Country.translate(locale: str) -> Country` (`.localize()` also reads fine; `.translate()` matches gettext's own vocabulary) returns a new DTO with `name`/`official_name` swapped to the localized string; `alpha2`/`alpha3`/`numeric`/`flag` stay untouched since codes don't translate. Same shape for `Subdivision.name`, and later `Currency`/`Language`/`Script` names. Out of scope: `aliases` (a separate, already-existing mechanism for colloquial/historical name variants, not systematic per-locale translation) and city names (GeoNames-sourced, no ISO/iso-codes backing; GeoNames has its own, much larger alternate-names-by-language file, a distinct future item). Catalogs load lazily and cache per `(domain, locale)`, the same `@cached_property` pattern `Registry` already uses for its indexes, so an unused locale costs nothing.

### Registry-level `language_code` support

`filter()` and `search()` accept an optional `language_code` kwarg; query mechanics differ between the two.

`filter()` is an exact match against `FilterIndex`, so a localized query reverse-translates cleanly: invert the target locale's gettext catalog into `{normalized_translated_string: english_canonical}`, resolve the localized `name` argument through it, run the existing English `FilterIndex.get()`, then translate the result DTOs back to the requested locale before returning.

`search()` cannot use the same reverse-translation step, since the reverse map is an exact-string lookup and a typo in the localized query (e.g. "Deutschlnd") has no catalog entry to resolve, which would defeat the fuzzy-match tolerance `search()` exists for. Instead, `search()` fuzzy-matches directly against a per-locale corpus built from the localized name strings themselves, then resolves the winning match to its canonical id. Countries (254 entities) already skip trigram pre-filtering under 300 records, so a per-locale corpus is cheap there; subdivisions (51k) are the same cost class as the existing ~3ms English search and should be built lazily per `(domain, locale)` rather than precomputed and shipped for every locale upfront. Cities have no ISO/iso-codes source and stay out of scope, so this never needs to scale to city-sized data.

`lookup()` matches on language-independent identifiers (`alpha2`, `alpha3`, `iso_code`, etc.), so it has no reverse-translation need; a `language_code` there would only mean "translate the returned DTO," equivalent to `.get(...).translate(locale)`.

### Open questions

- Which locales to ship: all of iso-codes' catalogs, or a curated subset. Leaning all, since gettext's fallback makes sparse coverage safe by default.
- Whether iso-codes' catalogs cover secondary fields (e.g. `Subdivision.type`) or only the primary name/official_name fields, not yet verified.
- Semantics of a cross-registry filter kwarg under `language_code`, e.g. `subdivisions.filter(country="Deutschland", language_code="de")`, where `country` references a different registry's translatable field.
- Actual size of the compiled `.mo` catalogs across all locales isn't confirmed yet, needs measuring before deciding to ship all of them.