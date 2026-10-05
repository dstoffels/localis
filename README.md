# localis

Fast, offline access to comprehensive data for **countries**, **subdivisions**, **cities**, the countries' **macroregions**, the **currencies** and **languages** they use, and the writing **scripts** languages are written in. Built on ISO 3166, ISO 4217, ISO 639-3, ISO 15924, GeoNames, Unicode CLDR and Wikidata datasets (updated monthly) with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **<stat key="data.countries.total:int">281</stat> countries** (<stat key="data.countries.historic:int">31</stat> historic) sourced and merged from ISO 3166-1, ISO 3166-3, and GeoNames
- 🗺️ **<stat key="data.subdivisions.total:int">51,711</stat> subdivisions** sourced and merged from ISO 3166-2 and GeoNames
- 🏙️ **<stat key="data.cities.total:int">235,970</stat> cities** sourced from GeoNames cities500.txt
- 🌐 **<stat key="data.macroregions.total:int">34</stat> macroregions** (<stat key="data.macroregions.regions:int">5</stat> regions, <stat key="data.macroregions.subregions:int">23</stat> subregions, <stat key="data.macroregions.groupings:int">6</stat> groupings) sourced from Unicode CLDR, with every current country placed in them
- 💱 **<stat key="data.currencies.total:int">178</stat> currencies** and funds from ISO 4217, with each current country's legal tender from Unicode CLDR
- ✍️ **<stat key="data.scripts.total:int">226</stat> scripts** from ISO 15924, with Unicode CLDR's English script names as aliases
- 🗣️ **<stat key="data.languages.total:int">7,923</stat> languages** from ISO 639-3, with Unicode CLDR's scripts for each and each current country's official languages
- 🔍 **Typo-tolerant search**: with a typo in the query, the intended record ranks first for <stat key="bench.registries.countries.accuracy.top1_pct:pct">99.3%</stat> of countries, <stat key="bench.registries.subdivisions.accuracy.top1_pct:pct">85.5%</stat> of subdivisions and <stat key="bench.registries.cities.accuracy.top1_pct:pct">91.3%</stat> of cities
- 📌 **Aliases**: support for colloquial, historic and alternate names

---

## Installation

```bash
pip install localis
```

---

## Requirements

- Python 3.11+
- `rapidfuzz` - Fast fuzzy string matching

---

## Quick Start

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

---

## Querying

Each dataset is represented by its registry: `countries`, `subdivisions`, `cities`, `macroregions`, `currencies`, `scripts` and `languages`, sharing a common query API.

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

```python
country = localis.countries.get(1)
subdivision = localis.subdivisions.get(1)
city = localis.cities.get(1)
macroregion = localis.macroregions.get(1)
currency = localis.currencies.get(1)
script = localis.scripts.get(1)
language = localis.languages.get(1)
```

**Returns:** the entity with that localis ID, or `None`

> ℹ️ IDs are only valid within the installed version; to store a reference, use [key](#key).

### lookup

Resolves a single record by an identifier other than its localis ID.

| Registry | Identifiers |
|---|---|
| `countries` | alpha-2 (`"GB"`), alpha-3 (`"GBR"`), numeric (`826`), a historic entry only by its `alpha_4` (`"CSHH"`, see [Historic Countries](#historic-countries)) |
| `subdivisions` | ISO 3166-2 code (`"US-CA"`), GeoNames code (`"US.CA"`) |
| `cities` | GeoNames ID (`5128581`) |
| `macroregions` | code (`"155"`, `"EU"`), name (`"Western Europe"`) |
| `currencies` | alpha-3 (`"EUR"`), numeric (`978`) |
| `scripts` | alpha-4 (`"Cyrl"`), numeric (`220`) |
| `languages` | ISO 639-3 (`"deu"`), ISO 639-1 (`"de"`), ISO 639-2/B (`"ger"`) |

```python
country = localis.countries.lookup("GB")
subdivision = localis.subdivisions.lookup("US-CA")
city = localis.cities.lookup(5128581)
macroregion = localis.macroregions.lookup("EU")
currency = localis.currencies.lookup("EUR")
script = localis.scripts.lookup("Cyrl")
language = localis.languages.lookup("de")
```

**Returns:** the entity, or `None`. A key that isn't a string or an int raises `TypeError`.

> ℹ️ `lookup()` matches identifiers only. Common abbreviations that aren't ISO codes, such as "UK" for the United Kingdom, are found by `filter(name=...)` and `search()`. M49 codes are zero-padded strings, so `macroregions.lookup("009")` finds Oceania and `lookup(9)` finds nothing.

### filter

Exact matches on any value a field indexes. Using multiple fields combines the conditions with a logical AND.

| Registry | Fields |
|---|---|
| `countries` | `name` (name, official name, common name or alias), `macroregion` (a region, subregion or grouping, by name or code), `currency` (by name or alpha-3), `language` (an official language, by name or ISO 639 code) |
| `subdivisions` | `name` (name or alias), `type`, `country` (name, common name, alpha-2, alpha-3 or numeric), `admin_level` (0 = non-administrative groupings, 1 = states/provinces, 2 = counties/districts, 3 = divisions below those) |
| `cities` | `name`, `country` (name, common name, alpha-2 or alpha-3), `subdivision` (any subdivision in the city's chain, by name, ISO code or its suffix (`"CA"`), or GeoNames code) |
| `currencies` | `name` |
| `scripts` | `name` (name or alias) |
| `languages` | `name` (name, inverted name or alias), `scope`, `type`, `script` (by alpha-4, name or alias, primary or secondary) |

```python
localis.countries.filter(name="UK")  # aliases and abbreviations match too
localis.countries.filter(macroregion="Western Europe")
localis.countries.filter(currency="EUR")  # countries whose legal tender includes the euro
localis.countries.filter(language="fr")  # countries where French has an official status
localis.languages.filter(script="Cyrl", type="living")
localis.subdivisions.filter(country="US", type="state")
localis.subdivisions.filter(admin_level=1, limit=10)
localis.cities.filter(country="US", subdivision="California", limit=20)

# Records with no value in a field
localis.subdivisions.filter(type=localis.MISSING)  # GeoNames-only subdivisions, which have no ISO type
localis.cities.filter(country="US", subdivision=localis.MISSING)  # US cities linked to no subdivision
localis.countries.filter(macroregion=localis.MISSING)  # historic countries placed in none (with include_historic set)
localis.countries.filter(currency=localis.MISSING)  # countries with no legal tender, such as Antarctica
localis.languages.filter(script=localis.MISSING)  # languages CLDR lists no script for
```

Pass `localis.MISSING` to match records with no value in a field (`None` ignores the field). A field the registry doesn't have raises `TypeError`, as does a call with no field.

**Returns:** a list of entities sorted by name. `limit` defaults to every match and must be at least 1.

### search

```python
for country, score in localis.countries.search("Germny", limit=5):
    print(f"{country.name}: {score:.2f}")
# Germany first, then weaker matches such as Guernsey

localis.subdivisions.search("Californa")
localis.cities.search("Springfeld, Illinois")  # context after the name narrows the match
localis.cities.search("Springfield", population_sort=True)  # the best matches, largest city first
localis.currencies.search("Swiss Frank")
localis.scripts.search("Devanagri")
localis.languages.search("Portugese")
```

A subdivision or city query can add context after the name: a subdivision's parent or country, or a city's first-level subdivision or country.

**Returns:** a list of `(entity, score)` pairs, best match first. Each score runs from 0 to 1, higher is better. `limit` defaults to 10 and must be at least 1.

### Iteration and len()

```python
for country in localis.countries:
    print(country.name)

total = len(localis.subdivisions)
```

> ℹ️ Historic countries are left out of `filter()`, `search()`, iteration and `len()` unless included (see [Historic Countries](#historic-countries)), and a population threshold narrows every cities query (see [Population Threshold](#population-threshold)).

---

## Entities

Results are typed dataclasses, listed field by field under each registry below. Each has `to_dict()` and `json()`, `str()` gives its JSON, and `key` is its stable reference (see [key](#key) below). A record nested in another, such as `subdivision.country`, `city.subdivisions`, `country.macroregions` or `country.currencies`, is its base form (`CountryBase`, `SubdivisionBase`, `MacroregionBase`, `CurrencyBase`), which keeps the fields marked Base in those tables. A nested record that carries facts about the relationship, such as a country's languages or a language's scripts, is its base form plus those facts (`CountryLanguage`, `LanguageScript`).

Every returned entity is built fresh; yours to mutate freely. Entities are also hashable, so they can be used in sets and as dict keys.

Every entity type, their base `Entity`, `Missing` and the registry classes (`CountryRegistry` and the rest) import from `localis` for type annotations.

```python
country = localis.countries.lookup("US")
country.to_dict()                # dict of every field
country.json()                   # the same, as a JSON string
localis.subdivisions.lookup("US-CA").country.alpha3  # "USA", from the nested CountryBase
```

### key

localis IDs are not stable across builds (`localis.__version__` gives the installed one). Use the `key` attribute to reliably reference entities instead, which returns the entity's stable lookup identifier. A nested record also carries its `key`.

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

ISO 3166-3 withdrawn countries are included in the dataset but excluded from `filter()`, `search()`, iteration and `len()` by default. The countries registry exposes `set_include_historic()` to toggle them on or off.

```python
localis.countries.include_historic   # False
len(localis.countries)               # current countries only

# Include historic entries
localis.countries.set_include_historic(True)
len(localis.countries)               # current and historic

localis.countries.set_include_historic(False)
```

`len(localis.countries)` is <stat key="data.countries.current:int">250</stat> by default and <stat key="data.countries.total:int">281</stat> with historic entries included.

> ⚠️ The toggle applies to every thread using `localis.countries`, so set it before sharing the registry between threads (see [Concurrency](#concurrency)).

`get()` and `lookup()` always find historic entries; `lookup()` finds them only by alpha_4.

```python
localis.countries.lookup("CSHH")  # Czechoslovakia
localis.countries.lookup("CS")    # None: a reused code never resolves a historic entry
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

```python
# Narrow the cache and all indexes to cities with population >= 15000
localis.cities.set_population_threshold(15000)

# Check the current threshold
localis.cities.population_threshold  # 15000

# Reset back to the full dataset
localis.cities.set_population_threshold(None)
```

Call `cities.set_population_threshold()` before first access so the registry only ever caches the narrowed dataset. Calling it after the cache or indexes are already built still works, but it invalidates them, so the next access rebuilds everything from scratch at the new threshold, paying the cache tax twice.

> ⚠️ The threshold applies to every thread using `localis.cities`, so set it before sharing the registry between threads (see [Concurrency](#concurrency)).

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

Every ISO 15924 code ships as published. Unicode CLDR's English names are aliases, so "Han" finds "Han (Hanzi, Kanji, Hanja)".

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

Every ISO 15924 code ships as ISO publishes it, including the special codes (`"Zyyy"` undetermined, `"Zxxx"` unwritten, `"Zmth"` mathematical notation) and the two entries marking the private-use range, `"Qaaa"` (start) and `"Qabx"` (end). ISO's names often carry other names in parentheses, such as "Han (Hanzi, Kanji, Hanja)"; Unicode CLDR's English names for the same code ("Han", "Simplified Han") are its aliases, so both are found by `filter(name=...)` and `search()`.

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

Every ISO 639-3 code ships as ISO publishes it: living, extinct, historical and constructed languages, macrolanguages such as Arabic and Chinese, and the special codes (`"und"` undetermined, `"mul"` multiple, `"zxx"` no linguistic content). A language's `scripts` come from Unicode CLDR, which covers <stat key="data.languages.with_scripts:int">811</stat> of them; the rest have none.

```python
german = localis.languages.lookup("de")
german.scripts  # [LanguageScript(alpha4="Latn", secondary=False, ...)]

for language in localis.countries.lookup("HK").languages:
    print(language.name, language.status, language.population_percent, language.script)
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

A language as one country recognizes it: every `LanguageBase` field plus three from Unicode CLDR. A country lists one per language and script CLDR gives an official status, ordered by `population_percent`.

| Field | Type | Example (Hong Kong's Chinese) | Notes |
|---|---|---|---|
| `status` | `LanguageStatus` | `"official"` | `"official"`, `"regional"` (official in part of the country) or `"de_facto"` (official in practice, such as English in the US) |
| `population_percent` | `float \| None` | `95.0` | CLDR's estimate of the population using it; shares overlap, since people use several languages |
| `script` | `ScriptBase \| None` | Han (Traditional variant) | the script CLDR gives the status for, so a language can appear once per script; `None` where CLDR names none |

---

## Performance

### Caching

All registries and their indexes are lazy-loaded on first use, incurring a cold start cost on whichever call touches them first. Any registry's dataset and indexes can be pre-loaded with `.force_cache()` to avoid this during queries, or you can simply access the registry/method to trigger the lazy loading upfront.

Each component is shown as load time / memory, measured for that registry alone.

| Registry | Records | Dataset | Lookup index | Filter index | Search index | Combined |
|---|---|---|---|---|---|---|
| Macroregions | <stat key="data.macroregions.total:int">34</stat> | <stat key="footprint.registries.macroregions.dataset.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.macroregions.dataset.memory_bytes:size">8KB</stat> | <stat key="footprint.registries.macroregions.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.macroregions.lookup_index.memory_bytes:size">6KB</stat> | n/a | n/a | **<stat key="footprint.registries.macroregions.combined.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.macroregions.combined.memory_bytes:size">14KB</stat>** |
| Currencies | <stat key="data.currencies.total:int">178</stat> | <stat key="footprint.registries.currencies.dataset.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.dataset.memory_bytes:size">28KB</stat> | <stat key="footprint.registries.currencies.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.lookup_index.memory_bytes:size">15KB</stat> | <stat key="footprint.registries.currencies.filter_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.filter_index.memory_bytes:size">20KB</stat> | <stat key="footprint.registries.currencies.search_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.currencies.search_index.memory_bytes:size">178KB</stat> | **<stat key="footprint.registries.currencies.combined.time_ms:load">~2ms</stat> / <stat key="footprint.registries.currencies.combined.memory_bytes:size">241KB</stat>** |
| Scripts | <stat key="data.scripts.total:int">226</stat> | <stat key="footprint.registries.scripts.dataset.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.scripts.dataset.memory_bytes:size">46KB</stat> | <stat key="footprint.registries.scripts.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.scripts.lookup_index.memory_bytes:size">19KB</stat> | <stat key="footprint.registries.scripts.filter_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.scripts.filter_index.memory_bytes:size">28KB</stat> | <stat key="footprint.registries.scripts.search_index.time_ms:load">~1ms</stat> / <stat key="footprint.registries.scripts.search_index.memory_bytes:size">228KB</stat> | **<stat key="footprint.registries.scripts.combined.time_ms:load">~2ms</stat> / <stat key="footprint.registries.scripts.combined.memory_bytes:size">321KB</stat>** |
| Languages | <stat key="data.languages.total:int">7,923</stat> | <stat key="footprint.registries.languages.dataset.time_ms:load">~11ms</stat> / <stat key="footprint.registries.languages.dataset.memory_bytes:size">2.8MB</stat> | <stat key="footprint.registries.languages.lookup_index.time_ms:load">~2ms</stat> / <stat key="footprint.registries.languages.lookup_index.memory_bytes:size">575KB</stat> | <stat key="footprint.registries.languages.filter_index.time_ms:load">~8ms</stat> / <stat key="footprint.registries.languages.filter_index.memory_bytes:size">1.3MB</stat> | <stat key="footprint.registries.languages.search_index.time_ms:load">~8ms</stat> / <stat key="footprint.registries.languages.search_index.memory_bytes:size">1.4MB</stat> | **<stat key="footprint.registries.languages.combined.time_ms:load">~28ms</stat> / <stat key="footprint.registries.languages.combined.memory_bytes:size">6.1MB</stat>** |
| Countries | <stat key="data.countries.total:int">281</stat> | <stat key="footprint.registries.countries.dataset.time_ms:load">~1ms</stat> / <stat key="footprint.registries.countries.dataset.memory_bytes:size">360KB</stat> | <stat key="footprint.registries.countries.lookup_index.time_ms:load">< 1ms</stat> / <stat key="footprint.registries.countries.lookup_index.memory_bytes:size">40KB</stat> | <stat key="footprint.registries.countries.filter_index.time_ms:load">~2ms</stat> / <stat key="footprint.registries.countries.filter_index.memory_bytes:size">223KB</stat> | <stat key="footprint.registries.countries.search_index.time_ms:load">~2ms</stat> / <stat key="footprint.registries.countries.search_index.memory_bytes:size">391KB</stat> | **<stat key="footprint.registries.countries.combined.time_ms:load">~5ms</stat> / <stat key="footprint.registries.countries.combined.memory_bytes:size">1014KB</stat>** |
| Subdivisions | <stat key="data.subdivisions.total:int">51,711</stat> | <stat key="footprint.registries.subdivisions.dataset.time_ms:load">~78ms</stat> / <stat key="footprint.registries.subdivisions.dataset.memory_bytes:size">14.2MB</stat> | <stat key="footprint.registries.subdivisions.lookup_index.time_ms:load">~16ms</stat> / <stat key="footprint.registries.subdivisions.lookup_index.memory_bytes:size">4.3MB</stat> | <stat key="footprint.registries.subdivisions.filter_index.time_ms:load">~66ms</stat> / <stat key="footprint.registries.subdivisions.filter_index.memory_bytes:size">11.5MB</stat> | <stat key="footprint.registries.subdivisions.search_index.time_ms:load">~60ms</stat> / <stat key="footprint.registries.subdivisions.search_index.memory_bytes:size">11.8MB</stat> | **<stat key="footprint.registries.subdivisions.combined.time_ms:load">~220ms</stat> / <stat key="footprint.registries.subdivisions.combined.memory_bytes:size">41.8MB</stat>** |
| Cities | <stat key="data.cities.total:int">235,970</stat> | <stat key="footprint.registries.cities.dataset.time_ms:load">~332ms</stat> / <stat key="footprint.registries.cities.dataset.memory_bytes:size">28.1MB</stat> | <stat key="footprint.registries.cities.lookup_index.time_ms:load">~73ms</stat> / <stat key="footprint.registries.cities.lookup_index.memory_bytes:size">1.8MB</stat> | <stat key="footprint.registries.cities.filter_index.time_ms:load">~281ms</stat> / <stat key="footprint.registries.cities.filter_index.memory_bytes:size">49.1MB</stat> | <stat key="footprint.registries.cities.search_index.time_ms:load">~191ms</stat> / <stat key="footprint.registries.cities.search_index.memory_bytes:size">41.9MB</stat> | **<stat key="footprint.registries.cities.combined.time_ms:load">~877ms</stat> / <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat>** |
| **Total** | **<stat key="data.totals.records:int">296,323</stat>** | **<stat key="footprint.totals.dataset.time_ms:load">~423ms</stat> / <stat key="footprint.totals.dataset.memory_bytes:size">45.5MB</stat>** | **<stat key="footprint.totals.lookup_index.time_ms:load">~92ms</stat> / <stat key="footprint.totals.lookup_index.memory_bytes:size">6.8MB</stat>** | **<stat key="footprint.totals.filter_index.time_ms:load">~357ms</stat> / <stat key="footprint.totals.filter_index.memory_bytes:size">62.2MB</stat>** | **<stat key="footprint.totals.search_index.time_ms:load">~263ms</stat> / <stat key="footprint.totals.search_index.memory_bytes:size">55.9MB</stat>** | **<stat key="footprint.totals.combined.time_ms:load">~1.13s</stat> / <stat key="footprint.totals.combined.memory_bytes:size">170.5MB</stat>** |

> ℹ️ A registry also loads the datasets it references (without their indexes) so a cold first call on cities also loads countries and subdivisions, for example.

> ⚠️ Fully caching cities and its indexes adds <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat> of memory. Calling `localis.cities.force_cache()` loads all of it upfront. You can call `cities.set_population_threshold(n)` before first access as a lever to control the memory footprint. At a threshold of <stat key="data.cities.threshold:int">15,000</stat>, cities drops from <stat key="data.cities.total:int">235,970</stat> to <stat key="data.cities.above_threshold:int">34,172</stat> and memory drops from <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat> to <stat key="footprint.cities_threshold.memory_bytes:size">28.4MB</stat>.



### Search Benchmarks

`get()`, `lookup()` and `filter()` return in microseconds on warm caches.

| Registry | Latency (p50 / p95) | Accuracy (top 10) | Top Result |
|---|---|---|---|
| Countries | <stat key="bench.registries.countries.search.p50_ms:latency">1.37ms</stat> / <stat key="bench.registries.countries.search.p95_ms:latency">4.17ms</stat> | <stat key="bench.registries.countries.accuracy.success_pct:pct">100.0%</stat> | <stat key="bench.registries.countries.accuracy.top1_pct:pct">99.3%</stat> |
| Subdivisions | <stat key="bench.registries.subdivisions.search.p50_ms:latency">2.7ms</stat> / <stat key="bench.registries.subdivisions.search.p95_ms:latency">4.97ms</stat> | <stat key="bench.registries.subdivisions.accuracy.success_pct:pct">97.3%</stat> | <stat key="bench.registries.subdivisions.accuracy.top1_pct:pct">85.5%</stat> |
| Cities | <stat key="bench.registries.cities.search.p50_ms:latency">6.75ms</stat> / <stat key="bench.registries.cities.search.p95_ms:latency">12ms</stat> | <stat key="bench.registries.cities.accuracy.success_pct:pct">98.4%</stat> | <stat key="bench.registries.cities.accuracy.top1_pct:pct">91.3%</stat> |

Accuracy tested on <stat key="bench.sample_size:int">5,000</stat> mangled-query samples per registry; cities' search additionally includes city + admin1 context. Measured on <stat key="footprint.host.cpu">11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz</stat> with Python <stat key="footprint.host.python">3.14.7</stat>.

---

## Concurrency

Registries are safe to share across threads, and a cold registry loads once even when several threads reach it together.

> ⚠️ Two settings change shared state for every thread: `cities.set_population_threshold()` and `countries.set_include_historic()`. Configure them before the registry is shared between threads, never while other threads are querying it.

### Batch searching

On free-threaded Python (3.14t), a thread pool searches in parallel:

```python
from concurrent.futures import ThreadPoolExecutor
import localis

localis.cities.force_cache()  # load once, before the threads start
with ThreadPoolExecutor() as pool:
    results = list(pool.map(localis.cities.search, queries))
```

On a standard build, use processes. Each worker loads its own copy of the data (up to <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat> for cities), so apply settings in the worker's initializer:

```python
from concurrent.futures import ProcessPoolExecutor
import localis

def init_worker():
    localis.cities.set_population_threshold(15000)  # repeat any setting the parent uses

def search_city(query):
    return localis.cities.search(query)

if __name__ == "__main__":  # workers import this module, so the pool only starts in the parent
    with ProcessPoolExecutor(initializer=init_worker) as pool:
        results = list(pool.map(search_city, queries, chunksize=500))
```

---

## Data Sources
Data in this project is kept current monthly from the following sources:

- **Countries**
  - **Canonical**: [ISO 3166-1](https://www.iso.org/iso-3166-country-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [ISO 3166-3](https://www.iso.org/iso-3166-country-codes.html) withdrawn/historic country codes, also via Debian's iso-codes project
  - **Merged**: [GeoNames](https://www.geonames.org/) `countryInfo.txt`
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

[`docs/methodology.md`](docs/methodology.md) is a complete, falsifiable account of how each dataset is built: the rules that combine these sources, how the results were validated, and where they are known to be wrong. [`unmerged_subdivisions.md`](docs/unmerged_subdivisions.md) lists every ISO subdivision currently without a GeoNames counterpart.

### Data licensing

The shipped data is derived from these sources, modified by localis's ingest pipeline, and remains under their licenses: ISO 3166, ISO 4217, ISO 639-3 and ISO 15924 data via iso-codes (LGPL-2.1-or-later), GeoNames (CC BY 4.0), Unicode CLDR (Unicode License v3) and Wikidata (CC0). [`src/localis/data/NOTICE`](src/localis/data/NOTICE), which ships with the data, attributes each source, and the full license texts are in [`LICENSES/`](LICENSES) and in the wheel's metadata. If you redistribute the data, keep that notice and those licenses with it.

---

## License

**Code**: MIT ([`LICENSE`](LICENSE)).
**Data**: its sources' licenses, listed under [Data licensing](#data-licensing).
The package's license expression is `MIT AND LGPL-2.1-or-later AND CC-BY-4.0 AND Unicode-3.0 AND CC0-1.0`.

---

## History
localis began with some database cleanup. I found myself writing mountains of bespoke code to parse inconsistent, dirty data while trying to reconcile pycountry, GeoNames and Wikidata to name a few (Google Places was not in the budget). When the pipeline was complete and the data finally cleaned, I realized this mountain of code could be useful for others who might need a reliable offline solution, so here we are! Over the past few years I've taken great care to build a robust, reliable dataset, wrapped in a simple, performant interface. I hope you find it useful and please don't hesitate to contribute or report any issues.

---

## Contributing
- [Pull requests welcome](https://github.com/dstoffels/localis)
- [Report issues](https://github.com/dstoffels/localis/issues)

Support this project:
- [GitHub Sponsors](https://github.com/sponsors/dstoffels)
- [PayPal](https://www.paypal.biz/danOstoffels)

### Contributors
- [@SchubmannM](https://github.com/SchubmannM): performance work in [#8](https://github.com/dstoffels/localis/pull/8) that inspired localis's `array('I')` index storage and lazy-loaded registries