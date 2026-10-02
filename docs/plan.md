# Project Plan
## Overview

This document outlines the project plan for the Localis project, detailing the objectives, scope, timeline, and key milestones.

## Objectives

- Reduce localis's shipped package size and runtime memory footprint, primarily driven by the cities dataset.
- Ship comprehensive datasets by default, and let the API narrow them ad hoc (population floors, locales) at query time rather than shipping multiple hard-tiered dataset variants.

## Features
Features currently in development, in priority order:

1. Add `Country.historic: HistoricInfo | None` for defunct entries (Serbia and Montenegro, Netherlands Antilles, etc.), cross-referenced against iso-codes' `iso_3166-3.json` (ISO's own list of ~30 withdrawn codes; mechanical lookup, not resolve-subdivisions-scale work). Nested object, not a bool, `None` for live countries, its presence alone is the flag. `HistoricInfo` shape matches the real source fields: `{alpha_4: str, withdrawal_date: str, comment: str | None}`. Historic entries key uniquely on `alpha_4`, not alpha2/alpha3, since ISO reused `CS` for two different historic entries (Czechoslovakia `CSHH`, Serbia and Montenegro `CSXX`); `filter()`/`search()` can still match historic entries by alpha2/alpha3 (may return both on a collision, which is fine, they return lists), but `lookup()` (unique-result by definition) only resolves a historic entry via `alpha_4` and never bare alpha2/alpha3, with the `CS` collision documented as a known limitation explaining why. A registry-level `include_historic` toggle (mirrors `CityRegistry`'s population-threshold `IndexFilterPredicate`/`Registry._is_id_allowed()` mechanism) includes/excludes historic entries from `filter()`/`search()`/iteration. GeoNames entries matching neither current ISO 3166-1 nor ISO 3166-3 (Clipperton Island, Diego Garcia, not actual countries) are excluded from ingest entirely. Kosovo (matches neither list, but a real functioning state) is a manual carve-out, stays live and non-historic.
2. Add `Currency` entity + `Country.currency` (ISO 4217, sourced from iso-codes' `iso_4217.json`, not GeoNames' embedded currency fields, since iso-codes is the authoritative source and already the same upstream `countries` data comes from)
3. Add `Language` entity + `Country.languages` (ISO 639, sourced from iso-codes' `iso_639-3.json`, same reasoning as currency; supersedes the old "implement native languages in countries" idea). Currency and Language close the honest gap identified against pycountry (which also covers ISO 4217/639), so both should ship before that comparison gets used as marketing material.
4. Add standalone `Script` reference table (ISO 15924, code → name only). Lowest priority of this batch: a language can be written in more than one script, so it isn't 1:1 with `Language` or `Country`; mostly used for font rendering and BCP-47 locale tags, not something to wire into other entities.

Blocked on the above, needs a dedicated design pass before implementation starts (see Localization section below for the open questions):
- Gettext-based name translation across `Country`/`Subdivision` (and `Currency`/`Language`/`Script` once they exist), including `language_code` support on `filter()`/`search()`.

## Subdivision admin-level model, cities schema side (needs a design pass)

ISO-sourced `admin_level` is no longer capped at 2: it's a recursive walk of ISO's own parent chain, depth 1 plus however many real (non-bypassed) ancestors sit above an entry, so a genuine 3rd+ generation (France's région → collectivité → département chain) resolves on its own without a special case. See `docs/methodology.md` §7 for the full mechanism, including the non-administrative-ancestor exceptions this also had to account for (Indonesia, DR, Cabo Verde, Ireland, Iceland, Lithuania, Malawi).

What's still open is purely downstream: `City.admin1`/`City.admin2` are two fixed fields backed by two dedicated TSV columns, and don't yet have anywhere to put a 3rd-level subdivision when one exists. Current thinking leans toward replacing both with an admin-level-ordered `list[SubdivisionBase]` for JSON/API consumers, but this is unsettled. Same version bump as the `Country.historic` work above. `SubdivisionModel.parent` (a single self-reference) already generalizes to arbitrary depth with no data-structure change needed, so this is purely a `City`-side gap. A major version bump is coming anyway for the languages/currencies/scripts additions, so this doesn't need to be solved in isolation.

## Backlog
- City radius feature using lat/lng to return nearby cities within a specified distance?
- Add filter() kwarg error handling for invalid arguments
- Implement custom exceptions (localis.exceptions module)?
- Set thread locks for concurrent access to registries
- Implement autocomplete for registries and/or global interface.
- Redevelop Wikidata SPARQL query and parsing logic for country alias enrichment.
- No ISO source maps countries to their language(s) (639 and 3166 don't cross-reference); evaluate Unicode CLDR's territory-language data for this.

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
- Reconsider Unicode CLDR as the translation data source instead of iso-codes' gettext catalogs; CLDR is more actively maintained and broader-coverage for exactly this kind of translated display-name data. Decide before implementation starts, not after.