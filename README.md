# localis

Fast, offline data for **countries**, **subdivisions**, **cities**, **macroregions**, **currencies**, **languages** and **scripts**, built from ISO 3166, ISO 4217, ISO 639-3, ISO 15924, GeoNames, Unicode CLDR and Wikidata (updated monthly), with exact lookups, filtering and typo-tolerant search.

> ⚠️ **localis 3.0 is in beta.** `pip install localis` still installs 2.1.x, which is no longer maintained; install the beta with `pip install --pre localis`. The [CHANGELOG](https://github.com/dstoffels/localis/blob/main/CHANGELOG.md#upgrading-from-210) lists what changed from 2.1, and [docs/versioning.md](https://github.com/dstoffels/localis/blob/main/docs/versioning.md#pre-releases) explains the beta.

## Features

- 🌍 **<stat key="data.countries.total:int">281</stat> countries** (<stat key="data.countries.historic:int">31</stat> historic) sourced and merged from ISO 3166-1, ISO 3166-3, GeoNames and Wikidata
- 🗺️ **<stat key="data.subdivisions.total:int">51,710</stat> subdivisions** sourced and merged from ISO 3166-2 and GeoNames
- 🏙️ **<stat key="data.cities.total:int">236,041</stat> cities** sourced from GeoNames cities500.txt
- 🌐 **<stat key="data.macroregions.total:int">34</stat> macroregions** (<stat key="data.macroregions.regions:int">5</stat> regions, <stat key="data.macroregions.subregions:int">23</stat> subregions, <stat key="data.macroregions.groupings:int">6</stat> groupings) sourced from Unicode CLDR, with every current country placed in them
- 💱 **<stat key="data.currencies.total:int">178</stat> currencies** and funds from ISO 4217, with each current country's legal tender from Unicode CLDR
- ✍️ **<stat key="data.scripts.total:int">226</stat> scripts** from ISO 15924, with Unicode CLDR's English script names as aliases
- 🗣️ **<stat key="data.languages.total:int">7,923</stat> languages** from ISO 639-3, with Unicode CLDR's scripts for each and each current country's official languages
- 🔍 **Typo-tolerant search**: with a typo in the query, the intended record ranks first for <stat key="bench.registries.countries.accuracy.top1_pct:pct">99.3%</stat> of countries, <stat key="bench.registries.subdivisions.accuracy.top1_pct:pct">93.7%</stat> of subdivisions and <stat key="bench.registries.cities.accuracy.top1_pct:pct">93.4%</stat> of cities
- 📌 **Aliases**: support for colloquial, historic and alternate names

## Installation

```bash
pip install --pre localis

uv add --prerelease allow localis
```

### Requirements

- Python 3.11+
- `rapidfuzz` - Fast fuzzy string matching

### Quick Start

```python
import localis

# Exact lookups by code
country = localis.countries.lookup("US")
print(country.name)  # "United States"

state = localis.subdivisions.lookup("US-CA")
print(state.name)  # "California"

# Filters: exact matches, combined with AND
cities = localis.cities.filter(country="US", subdivision="California", limit=10)

# Typo-tolerant search: (result, score) pairs, best first
results = localis.countries.search("Austrlia")
print(results[0][0].name)  # "Australia"
```

## Querying

Each dataset is a registry sharing one query API.

| Registry | `get` | `lookup` | `filter` | `search` | Iteration |
|---|---|---|---|---|---|
| `countries` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `subdivisions` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `cities` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `macroregions` | ✓ | ✓ | | | ✓ |
| `currencies` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `scripts` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `languages` | ✓ | ✓ | ✓ | ✓ | ✓ |

Lookups, filters and search ignore case and accents, so "sao paulo" finds São Paulo and "strasse" finds Straße.

### get

**Returns:** the entity with that localis ID, or `None`. IDs are only valid within the installed version; to store a reference, use [key](#key).

```python
localis.countries.get(1)
```

### lookup

Resolves a record by an identifier other than its localis ID. Identifiers only: "UK" isn't an ISO code, so find it with `filter(name=...)` or `search()`.

**Returns:** the entity, or `None`. A key that isn't a string or an int raises `TypeError`.

| Registry | Identifiers |
|---|---|
| `countries` | alpha-2 (`"GB"`), alpha-3 (`"GBR"`), numeric (`826`), a historic entry only by its `alpha_4` (`"CSHH"`, see [Historic Countries](#historic-countries)) |
| `subdivisions` | ISO 3166-2 code (`"US-CA"`), GeoNames code (`"US.CA"`) |
| `cities` | GeoNames ID (`5128581`) |
| `macroregions` | code (`"155"`, `"EU"`), name (`"Western Europe"`); M49 codes are zero-padded strings, so `lookup(9)` finds nothing |
| `currencies` | alpha-3 (`"EUR"`), numeric (`978`) |
| `scripts` | alpha-4 (`"Cyrl"`), numeric (`220`) |
| `languages` | ISO 639-3 (`"deu"`), ISO 639-1 (`"de"`), ISO 639-2/B (`"ger"`) |

```python
# "GB", "GBR" and 826 all find the United Kingdom
localis.countries.lookup("GBR")

# a numeric code or GeoNames ID as an int
localis.cities.lookup(5128581)
```

### filter

Exact matches on any value a field indexes. Using multiple fields combines the conditions with a logical AND. Pass `localis.MISSING` to match records with no value in a field (`None` ignores the field). A field the registry doesn't have raises `TypeError`, as does a call with no field.

**Returns:** a list of entities sorted by name. `limit` defaults to every match and must be at least 1.

#### Fields by Registry

**Countries**
- `name` (name, official name, common name or alias)
- `macroregion` (a region, subregion or grouping, by name or code)
- `currency` (by name or alpha-3)
- `language` (an official language, by name or ISO 639 code)
- `continent` (by name or GeoNames code)

**Subdivisions**
- `name` (name or alias)
- `type`
- `country` (name, common name, alpha-2, alpha-3 or numeric, as `76` or `"076"`)
- `admin_level` (0 = non-administrative groupings, 1 = states/provinces, 2 = counties/districts, 3 = divisions below those)

**Cities**
- `name`
- `country` (name, common name, alpha-2 or alpha-3)
- `subdivision` (any subdivision in the city's chain, by name, ISO code or its suffix (`"CA"`), or GeoNames code)

**Languages**
- `name` (name, inverted name or alias)
- `scope`
- `type`
- `script` (by alpha-4, name or alias, primary or secondary)

**Currencies**
- `name`

**Scripts**
- `name` (name or alias)

```python
# aliases and abbreviations match too
localis.countries.filter(name="UK")

# countries whose legal tender includes the euro
localis.countries.filter(currency="EUR")

# fields combine with AND
localis.cities.filter(country="US", subdivision="California", limit=20)

# GeoNames-only subdivisions, which have no ISO type
localis.subdivisions.filter(type=localis.MISSING)
```

### search

Typo-tolerant matching on names and aliases. A subdivision or city query can add context after the name: a subdivision's parent or country, or a city's first-level subdivision or country.

**Returns:** a list of `(entity, score)` pairs, best first, scored 0 to 1; cities with the same score rank larger first. `limit` defaults to 10 and must be at least 1.

```python
# Germany first, then weaker matches such as Guernsey
localis.countries.search("Germny", limit=5)

# context after the name narrows the match
localis.cities.search("Springfeld, Illinois")

# the best matches, largest city first
localis.cities.search("Springfield", population_sort=True)
```

### Iteration and len()

```python
for country in localis.countries:
    print(country.name)

total = len(localis.subdivisions)
```

> ℹ️ Historic countries are left out unless included (see [Historic Countries](#historic-countries)), and a [population threshold](#population-threshold) narrows every cities query.

## Entities

Results are typed dataclasses with `to_dict()` and `json()`; `str()` gives the JSON. Each is built fresh, so it's yours to change, and hashable. A record nested in another, such as `subdivision.country`, is its base form (`CountryBase`, `SubdivisionBase`, ...), keeping the fields marked Base below; one that carries facts about the relationship adds them (`CountryLanguage`, `LanguageScript`). Every entity type, `Entity`, `Missing` and the registry classes import from `localis` for type annotations.

```python
# every field, nested records included
localis.countries.lookup("US").to_dict()

# "USA", from the nested CountryBase
localis.subdivisions.lookup("US-CA").country.alpha3
```

### key

IDs change between versions (`localis.__version__` gives the installed one). Store `key` instead: `lookup()` resolves it in any later version. Nested records carry it too.

```python
# 5128581, safe to persist
saved = city.key

# the same city, in this version or a later one
city = localis.cities.lookup(saved)
```

| Registry | `key` |
|---|---|
| `countries` | `alpha2`, or `historic.alpha_4` for a historic entry |
| `subdivisions` | `iso_code`, or `geonames_code` for a subdivision ISO doesn't list |
| `cities` | `geonames_id` |
| `macroregions` | `code` |
| `currencies` | `alpha3` |
| `scripts` | `alpha4` |
| `languages` | `alpha3` (ISO 639-3) |

### Countries

#### Historic Countries

ISO 3166-3 withdrawn countries are left out of `filter()`, `search()`, iteration and `len()` unless included with `set_include_historic(True)` (`include_historic` reads the setting). `get()` always finds them, and `lookup()` finds them by `alpha_4` only. `len(localis.countries)` is <stat key="data.countries.current:int">250</stat> by default and <stat key="data.countries.total:int">281</stat> with them.

```python
# Czechoslovakia
localis.countries.lookup("CSHH")

# None: a reused code never resolves a historic entry
localis.countries.lookup("CS")
```

#### Country Object

A ✓ under Base marks a field the nested `CountryBase` also has.

| Field | Type | Example (`"US"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"US"` | stable reference to store; `alpha_4` for a historic entry | ✓ |
| `name` | `str` | `"United States"` | ISO 3166-1 name, as published | ✓ |
| `official_name` | `str \| None` | `"United States of America"` | ISO 3166-1 official name; `None` where ISO has none | |
| `common_name` | `str \| None` | `None` | Debian iso-codes' everyday name where it differs, such as "South Korea" for "Korea, Republic of" | |
| `alpha2` | `str` | `"US"` | | ✓ |
| `alpha3` | `str \| None` | `"USA"` | | ✓ |
| `numeric` | `int \| None` | `840` | ISO 3166-1 numeric code; `None` for Kosovo, which has no ISO assignment | |
| `geonames_id` | `int \| None` | `6252001` | | ✓ |
| `aliases` | `list[str]` | | alternate names from GeoNames and Wikidata | |
| `flag` | `str \| None` | `"🇺🇸"` | Unicode flag emoji | |
| `historic` | `HistoricInfo \| None` | `None` | set only for withdrawn ISO 3166-3 countries | |
| `continent` | `Continent \| None` | North America | GeoNames' continent (see [Continent](#continent)); `None` for a country GeoNames doesn't list | |
| `macroregions` | `list[MacroregionBase]` | [Americas, Northern America] | CLDR path, region then subregion; `[]` for most historic countries | |
| `groupings` | `list[MacroregionBase]` | [North America, United Nations] | CLDR groupings the country belongs to | |
| `currencies` | `list[CurrencyBase]` | [US Dollar] | legal tender in use, per CLDR, in CLDR's order; `[]` for historic countries | |
| `languages` | `list[CountryLanguage]` | [English, Spanish, Hawaiian] | languages with an official status, per CLDR, by population share; `[]` for historic countries (see [CountryLanguage](#countrylanguage)) | |

##### HistoricInfo

| Field | Type | Example (`"CSHH"`) | Notes |
|---|---|---|---|
| `alpha_4` | `str` | `"CSHH"` | ISO 3166-3 withdrawal code, unique to the entry |
| `withdrawal_date` | `str` | `"1993-01-01"` | |
| `comment` | `str \| None` | | ISO's comment |

##### Continent

GeoNames enrichment, not an authoritative standard, and separate from macroregions, whose memberships can differ (GeoNames puts Cyprus in Europe, CLDR in Western Asia).

| Field | Type | Example (`"US"`) | Notes |
|---|---|---|---|
| `name` | `str` | `"North America"` | |
| `geonames_code` | `str` | `"NA"` | GeoNames' continent code, not an ISO code |
| `geonames_id` | `int` | `6255149` | |

### Subdivisions

#### Subdivision Object

A ✓ under Base marks a field the nested `SubdivisionBase` also has.

| Field | Type | Example (`"US-CA"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"US-CA"` | stable reference to store; the GeoNames code where ISO doesn't list the subdivision | ✓ |
| `name` | `str` | `"California"` | ISO 3166-2 name where ISO lists the subdivision, otherwise GeoNames' | ✓ |
| `iso_code` | `str \| None` | `"US-CA"` | `None` for a GeoNames-only subdivision | ✓ |
| `geonames_code` | `str \| None` | `"US.CA"` | GeoNames admin code; `None` for an ISO-only subdivision | ✓ |
| `geonames_id` | `int \| None` | `5332921` | `None` for an ISO-only subdivision | ✓ |
| `type` | `str \| None` | `"State"` | ISO type; `None` for a GeoNames-only subdivision | ✓ |
| `admin_level` | `int` | `1` | 0 = non-administrative grouping, 1 = top-level, 2 = second-level, 3 = below that | ✓ |
| `parent` | `SubdivisionBase \| None` | `None` | the subdivision it sits in | |
| `country` | `CountryBase` | United States | | |
| `aliases` | `list[str]` | | alternate names | |

### Cities

#### Population Threshold

Narrows the cache and every index to cities of at least that population (`population_threshold` reads it). Set it before first access; changing it later rebuilds the cache and indexes.

```python
localis.cities.set_population_threshold(15000)

# Builds the cache with ~34178 cities on next access
len(localis.cities)

# back to every city
localis.cities.set_population_threshold(None)
```

#### City Object

| Field | Type | Example (`5128581`) | Notes |
|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version |
| `key` | `int` | `5128581` | stable reference to store, the GeoNames ID |
| `geonames_id` | `int` | `5128581` | |
| `name` | `str` | `"New York"` | GeoNames' name, or its ASCII form where the name is in another script |
| `subdivisions` | `list[SubdivisionBase]` | | the city's full subdivision chain, ordered by `admin_level` ascending |
| `country` | `CountryBase` | United States | |
| `population` | `int` | | GeoNames population; `0` where unknown |
| `lat` | `float` | `40.71427` | |
| `lng` | `float` | `-74.00597` | |

### Macroregions

#### Macroregion Object

A ✓ under Base marks a field the nested `MacroregionBase` also has.

| Field | Type | Example (`"155"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"155"` | stable reference to store, the code | ✓ |
| `name` | `str` | `"Western Europe"` | CLDR English name | ✓ |
| `code` | `str` | `"155"` | M49 numeric code as a zero-padded string, or CLDR's letter code (`"QO"`, `"EU"`) | ✓ |
| `type` | `MacroregionType` | `"subregion"` | `"region"`, `"subregion"` or `"grouping"` | ✓ |
| `parent` | `MacroregionBase \| None` | Europe | a subregion's region, or the region CLDR files a grouping under | |

### Currencies

Every ISO 4217 code, funds, precious metals and testing codes included. Countries' legal tender comes from Unicode CLDR (see [Country Object](#country-object)).

#### Currency Object

A ✓ under Base marks a field the nested `CurrencyBase` also has.

| Field | Type | Example (`"EUR"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"EUR"` | stable reference to store, the alpha-3 | ✓ |
| `name` | `str` | `"Euro"` | ISO 4217 name, as published | ✓ |
| `alpha3` | `str` | `"EUR"` | | ✓ |
| `numeric` | `int \| None` | `978` | ISO 4217 numeric code | |

### Scripts

Every ISO 15924 code, special and private-use codes included (`"Zyyy"`, `"Qaaa"`). Unicode CLDR's English names are aliases, so "Han" finds "Han (Hanzi, Kanji, Hanja)".

#### Script Object

A ✓ under Base marks a field the nested `ScriptBase` also has.

| Field | Type | Example (`"Deva"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"Deva"` | stable reference to store, the alpha-4 | ✓ |
| `name` | `str` | `"Devanagari (Nagari)"` | ISO 15924 name, as published | ✓ |
| `alpha4` | `str` | `"Deva"` | | ✓ |
| `numeric` | `int \| None` | `315` | ISO 15924 numeric code | |
| `aliases` | `list[str]` | ["Devanagari"] | Unicode CLDR's English names for the code, where they differ from ISO's | |

### Languages

Every ISO 639-3 code, macrolanguages and special codes (`"und"`, `"mul"`) included. Scripts come from Unicode CLDR, which covers <stat key="data.languages.with_scripts:int">811</stat> languages; the rest have none.

```python
# [LanguageScript(alpha4="Latn", secondary=False, ...)]
localis.languages.lookup("de").scripts

# Hong Kong's official languages, by population share
localis.countries.lookup("HK").languages
```

#### Language Object

A ✓ under Base marks a field the nested `LanguageBase` also has.

| Field | Type | Example (`"deu"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"deu"` | stable reference to store, the ISO 639-3 code | ✓ |
| `name` | `str` | `"German"` | ISO 639-3 name, as published | ✓ |
| `alpha3` | `str` | `"deu"` | ISO 639-3 code | ✓ |
| `alpha2` | `str \| None` | `"de"` | ISO 639-1 code, for the <stat key="data.languages.with_alpha2:int">184</stat> languages that have one | ✓ |
| `bibliographic` | `str \| None` | `"ger"` | ISO 639-2/B code, where it differs from the 639-3 one | |
| `scope` | `LanguageScope` | `"individual"` | `"individual"`, `"macrolanguage"` or `"special"` | |
| `type` | `LanguageType` | `"living"` | `"living"`, `"extinct"`, `"historical"`, `"constructed"` or `"special"` | |
| `inverted_name` | `str \| None` | `None` | ISO's name with the qualifier moved last, such as "Arabic, Algerian Saharan" | |
| `aliases` | `list[str]` | ["Austrian German", ...] | Unicode CLDR's English names for the language and its regional and script forms, where they differ from ISO's | |
| `scripts` | `list[LanguageScript]` | [Latin] | per CLDR, primary scripts first; see [LanguageScript](#languagescript) | |

#### LanguageScript

A script as one language uses it: every `ScriptBase` field plus `secondary`.

| Field | Type | Notes |
|---|---|---|
| `secondary` | `bool` | CLDR's rule: `True` when the language isn't a modern language or the script isn't a modern script, such as Arabic written in Syriac or anything in Sanskrit |

`languages.filter(script=...)` matches primary and secondary scripts alike.

#### CountryLanguage

A language as one country recognizes it: every `LanguageBase` field plus three from Unicode CLDR, one per language and script with an official status.

| Field | Type | Example (Hong Kong's Chinese) | Notes |
|---|---|---|---|
| `status` | `LanguageStatus` | `"official"` | `"official"`, `"regional"` (official in part of the country) or `"de_facto"` (official in practice, such as English in the US) |
| `population_percent` | `float \| None` | `95.0` | CLDR's estimate of the population using it; shares overlap, since people use several languages |
| `script` | `ScriptBase \| None` | Han (Traditional variant) | the script CLDR gives the status for, so a language can appear once per script; `None` where CLDR names none |

## Performance

### Caching

Registries and their indexes load on first use; `force_cache()` loads one upfront. Each cell is load time / memory for that registry alone.

| Registry | Records | Dataset | Lookup index | Filter index | Search index | Combined |
|---|---|---|---|---|---|---|
| Macroregions | <stat key="data.macroregions.total:int">34</stat> | <stat key="footprint.registries.macroregions.dataset.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.macroregions.dataset.memory_bytes:size">7KB</stat> | <stat key="footprint.registries.macroregions.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.macroregions.lookup_index.memory_bytes:size">6KB</stat> | n/a | n/a | **<stat key="footprint.registries.macroregions.combined.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.macroregions.combined.memory_bytes:size">13KB</stat>** |
| Currencies | <stat key="data.currencies.total:int">178</stat> | <stat key="footprint.registries.currencies.dataset.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.dataset.memory_bytes:size">29KB</stat> | <stat key="footprint.registries.currencies.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.lookup_index.memory_bytes:size">15KB</stat> | <stat key="footprint.registries.currencies.filter_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.filter_index.memory_bytes:size">20KB</stat> | <stat key="footprint.registries.currencies.search_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.search_index.memory_bytes:size">181KB</stat> | **<stat key="footprint.registries.currencies.combined.time_ms:load">~2ms</stat> / <stat key="footprint.registries.currencies.combined.memory_bytes:size">245KB</stat>** |
| Scripts | <stat key="data.scripts.total:int">226</stat> | <stat key="footprint.registries.scripts.dataset.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.scripts.dataset.memory_bytes:size">48KB</stat> | <stat key="footprint.registries.scripts.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.scripts.lookup_index.memory_bytes:size">19KB</stat> | <stat key="footprint.registries.scripts.filter_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.scripts.filter_index.memory_bytes:size">28KB</stat> | <stat key="footprint.registries.scripts.search_index.time_ms:load">~1ms</stat> / <stat key="footprint.registries.scripts.search_index.memory_bytes:size">231KB</stat> | **<stat key="footprint.registries.scripts.combined.time_ms:load">~2ms</stat> / <stat key="footprint.registries.scripts.combined.memory_bytes:size">327KB</stat>** |
| Languages | <stat key="data.languages.total:int">7,923</stat> | <stat key="footprint.registries.languages.dataset.time_ms:load">~14ms</stat> / <stat key="footprint.registries.languages.dataset.memory_bytes:size">1.9MB</stat> | <stat key="footprint.registries.languages.lookup_index.time_ms:load">~3ms</stat> / <stat key="footprint.registries.languages.lookup_index.memory_bytes:size">589KB</stat> | <stat key="footprint.registries.languages.filter_index.time_ms:load">~9ms</stat> / <stat key="footprint.registries.languages.filter_index.memory_bytes:size">1.4MB</stat> | <stat key="footprint.registries.languages.search_index.time_ms:load">~11ms</stat> / <stat key="footprint.registries.languages.search_index.memory_bytes:size">1.5MB</stat> | **<stat key="footprint.registries.languages.combined.time_ms:load">~38ms</stat> / <stat key="footprint.registries.languages.combined.memory_bytes:size">5.4MB</stat>** |
| Countries | <stat key="data.countries.total:int">281</stat> | <stat key="footprint.registries.countries.dataset.time_ms:load">~2ms</stat> / <stat key="footprint.registries.countries.dataset.memory_bytes:size">373KB</stat> | <stat key="footprint.registries.countries.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.countries.lookup_index.memory_bytes:size">41KB</stat> | <stat key="footprint.registries.countries.filter_index.time_ms:load">~2ms</stat> / <stat key="footprint.registries.countries.filter_index.memory_bytes:size">233KB</stat> | <stat key="footprint.registries.countries.search_index.time_ms:load">~5ms</stat> / <stat key="footprint.registries.countries.search_index.memory_bytes:size">474KB</stat> | **<stat key="footprint.registries.countries.combined.time_ms:load">~10ms</stat> / <stat key="footprint.registries.countries.combined.memory_bytes:size">1.1MB</stat>** |
| Subdivisions | <stat key="data.subdivisions.total:int">51,710</stat> | <stat key="footprint.registries.subdivisions.dataset.time_ms:load">~95ms</stat> / <stat key="footprint.registries.subdivisions.dataset.memory_bytes:size">14.6MB</stat> | <stat key="footprint.registries.subdivisions.lookup_index.time_ms:load">~23ms</stat> / <stat key="footprint.registries.subdivisions.lookup_index.memory_bytes:size">4.5MB</stat> | <stat key="footprint.registries.subdivisions.filter_index.time_ms:load">~77ms</stat> / <stat key="footprint.registries.subdivisions.filter_index.memory_bytes:size">12.2MB</stat> | <stat key="footprint.registries.subdivisions.search_index.time_ms:load">~63ms</stat> / <stat key="footprint.registries.subdivisions.search_index.memory_bytes:size">12.4MB</stat> | **<stat key="footprint.registries.subdivisions.combined.time_ms:load">~258ms</stat> / <stat key="footprint.registries.subdivisions.combined.memory_bytes:size">43.7MB</stat>** |
| Cities | <stat key="data.cities.total:int">236,041</stat> | <stat key="footprint.registries.cities.dataset.time_ms:load">~422ms</stat> / <stat key="footprint.registries.cities.dataset.memory_bytes:size">29.5MB</stat> | <stat key="footprint.registries.cities.lookup_index.time_ms:load">~111ms</stat> / <stat key="footprint.registries.cities.lookup_index.memory_bytes:size">1.9MB</stat> | <stat key="footprint.registries.cities.filter_index.time_ms:load">~341ms</stat> / <stat key="footprint.registries.cities.filter_index.memory_bytes:size">51.5MB</stat> | <stat key="footprint.registries.cities.search_index.time_ms:load">~205ms</stat> / <stat key="footprint.registries.cities.search_index.memory_bytes:size">44.0MB</stat> | **<stat key="footprint.registries.cities.combined.time_ms:load">~1.08s</stat> / <stat key="footprint.registries.cities.combined.memory_bytes:size">126.9MB</stat>** |
| **Total** | **<stat key="data.totals.records:int">296,393</stat>** | **<stat key="footprint.totals.dataset.time_ms:load">~534ms</stat> / <stat key="footprint.totals.dataset.memory_bytes:size">46.4MB</stat>** | **<stat key="footprint.totals.lookup_index.time_ms:load">~138ms</stat> / <stat key="footprint.totals.lookup_index.memory_bytes:size">7.1MB</stat>** | **<stat key="footprint.totals.filter_index.time_ms:load">~429ms</stat> / <stat key="footprint.totals.filter_index.memory_bytes:size">65.4MB</stat>** | **<stat key="footprint.totals.search_index.time_ms:load">~288ms</stat> / <stat key="footprint.totals.search_index.memory_bytes:size">58.7MB</stat>** | **<stat key="footprint.totals.combined.time_ms:load">~1.39s</stat> / <stat key="footprint.totals.combined.memory_bytes:size">177.7MB</stat>** |

A registry also loads the datasets it references, without their indexes: a cold call on cities loads countries and subdivisions too.

> ⚠️ A [population threshold](#population-threshold) is the lever on memory: at <stat key="data.cities.threshold:int">15,000</stat>, cities drop from <stat key="data.cities.total:int">236,041</stat> to <stat key="data.cities.above_threshold:int">34,178</stat> and their memory from <stat key="footprint.registries.cities.combined.memory_bytes:size">126.9MB</stat> to <stat key="footprint.cities_threshold.memory_bytes:size">29.8MB</stat>.

### Search Benchmarks

`get()`, `lookup()` and `filter()` return in microseconds on warm caches.

| Registry | Latency (p50 / p95) | Queries | Accuracy (top 10) | Top Result |
|---|---|---|---|---|
| Countries | <stat key="bench.registries.countries.search.p50_ms:latency">1.48ms</stat> / <stat key="bench.registries.countries.search.p95_ms:latency">4.38ms</stat> | <stat key="bench.registries.countries.accuracy.queries:int">423</stat> | <stat key="bench.registries.countries.accuracy.success_pct:pct">100.0%</stat> | <stat key="bench.registries.countries.accuracy.top1_pct:pct">99.3%</stat> |
| Subdivisions | <stat key="bench.registries.subdivisions.search.p50_ms:latency">3.32ms</stat> / <stat key="bench.registries.subdivisions.search.p95_ms:latency">7.72ms</stat> | <stat key="bench.registries.subdivisions.accuracy.queries:int">7,009</stat> | <stat key="bench.registries.subdivisions.accuracy.success_pct:pct">98.0%</stat> | <stat key="bench.registries.subdivisions.accuracy.top1_pct:pct">93.7%</stat> |
| Cities | <stat key="bench.registries.cities.search.p50_ms:latency">7.98ms</stat> / <stat key="bench.registries.cities.search.p95_ms:latency">14.5ms</stat> | <stat key="bench.registries.cities.accuracy.queries:int">4,999</stat> | <stat key="bench.registries.cities.accuracy.success_pct:pct">98.8%</stat> | <stat key="bench.registries.cities.accuracy.top1_pct:pct">93.4%</stat> |

Accuracy is measured on names and aliases, each with at least one typo, of up to <stat key="bench.sample_size:int">5,000</stat> sampled records per registry; city queries add the admin1. A record sharing the sampled one's name (and a city's admin1) counts as a hit. Measured on <stat key="bench.host.cpu">11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz</stat> with Python <stat key="bench.host.python">3.14.7</stat>.

## Concurrency

Registries are safe to share across threads, and a cold registry loads once even when several threads reach it together.

> ⚠️ `cities.set_population_threshold()` and `countries.set_include_historic()` apply to every thread: set them before sharing the registry, never while other threads query it.

### Batch searching

On free-threaded Python (3.14t), a thread pool searches in parallel:

```python
from concurrent.futures import ThreadPoolExecutor
import localis

# load once, before the threads start
localis.cities.force_cache()
with ThreadPoolExecutor() as pool:
    results = list(pool.map(localis.cities.search, queries))
```

On a standard build, use processes. Each worker loads its own copy of the data (up to <stat key="footprint.registries.cities.combined.memory_bytes:size">126.9MB</stat> for cities) and needs the parent's settings repeated:

```python
from concurrent.futures import ProcessPoolExecutor
import localis

def init_worker():
    localis.cities.set_population_threshold(15000)

def search_city(query):
    return localis.cities.search(query)

# workers import this module, so the pool only starts in the parent
if __name__ == "__main__":
    with ProcessPoolExecutor(initializer=init_worker) as pool:
        results = list(pool.map(search_city, queries, chunksize=500))
```

## Data Sources

Refreshed monthly from:

- **Countries**
  - **Canonical**: [ISO 3166-1](https://www.iso.org/iso-3166-country-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [ISO 3166-3](https://www.iso.org/iso-3166-country-codes.html) withdrawn/historic country codes, also via Debian's iso-codes project
  - **Merged**: [GeoNames](https://www.geonames.org/) `countryInfo.txt`, continents included
  - **Merged**: Additional country aliases queried from [Wikidata](https://www.wikidata.org/): English labels, alternative labels and short names
- **Subdivisions**
  - **Canonical**: [ISO 3166-2](https://www.iso.org/iso-3166-country-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [GeoNames](https://www.geonames.org/) `admin1CodesASCII.txt` and `admin2Codes.txt`
  - **Merged**: [Wikidata](https://www.wikidata.org/) (ISO 3166-2 code ↔ GeoNames id)
  - **Merged**: Additional subdivision aliases from GeoNames' `alternateNamesV2` dump (Latin-script names only, filtered by [Unicode CLDR](https://cldr.unicode.org/)'s official-language data per country)
- **Cities**
  - [GeoNames](https://www.geonames.org/) `cities500.txt` dataset
- **Macroregions**
  - [Unicode CLDR](https://cldr.unicode.org/) territory containment and English territory names
- **Currencies**
  - **Canonical**: [ISO 4217](https://www.iso.org/iso-4217-currency-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: each country's legal tender from [Unicode CLDR](https://cldr.unicode.org/)'s currency data
- **Scripts**
  - **Canonical**: [ISO 15924](https://www.unicode.org/iso15924/) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [Unicode CLDR](https://cldr.unicode.org/)'s English script names, as aliases
- **Languages**
  - **Canonical**: [ISO 639-3](https://iso639-3.sil.org/) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [Unicode CLDR](https://cldr.unicode.org/)'s English language names as aliases, each language's scripts, and each country's official languages

Names ship in Latin script.

[`docs/methodology.md`](https://github.com/dstoffels/localis/blob/main/docs/methodology.md) documents how each dataset is built and validated, and where it's known to be wrong. [`unmerged_subdivisions.md`](https://github.com/dstoffels/localis/blob/main/docs/unmerged_subdivisions.md) lists every ISO subdivision without a GeoNames counterpart.

### Data licensing

The shipped data is modified from these sources and stays under their licenses: iso-codes (LGPL-2.1-or-later), GeoNames (CC BY 4.0), Unicode CLDR (Unicode License v3) and Wikidata (CC0). [`src/localis/data/NOTICE`](https://github.com/dstoffels/localis/blob/main/src/localis/data/NOTICE) attributes each source, and the license texts are in [`LICENSES/`](https://github.com/dstoffels/localis/tree/main/LICENSES) and the wheel's metadata. Keep both with the data if you redistribute it.

## License

**Code**: MIT ([`LICENSE`](https://github.com/dstoffels/localis/blob/main/LICENSE)).
**Data**: its sources' licenses, listed under [Data licensing](#data-licensing).
The package's license expression is `MIT AND LGPL-2.1-or-later AND CC-BY-4.0 AND Unicode-3.0 AND CC0-1.0`.

## History

localis began with some database cleanup. I found myself writing mountains of bespoke code to parse inconsistent, dirty data while trying to reconcile pycountry, GeoNames and Wikidata to name a few (Google Places was not in the budget). When the pipeline was complete and the data finally cleaned, I realized this mountain of code could be useful for others who might need a reliable offline solution, so here we are! Over the past few years I've taken great care to build a robust, reliable dataset, wrapped in a simple, performant interface. I hope you find it useful and please don't hesitate to contribute or report any issues.

## Contributing

- [Pull requests welcome](https://github.com/dstoffels/localis)
- [Report issues](https://github.com/dstoffels/localis/issues)

Support this project:
- [GitHub Sponsors](https://github.com/sponsors/dstoffels)
- [PayPal](https://www.paypal.biz/danOstoffels)

### Contributors
- [@SchubmannM](https://github.com/SchubmannM): performance work in [#8](https://github.com/dstoffels/localis/pull/8) that inspired localis's `array('I')` index storage and lazy-loaded registries