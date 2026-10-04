# localis

Fast, offline access to comprehensive data for **countries**, **subdivisions**, **cities**, the **macroregions** countries sit in and the **currencies** they use. Built on ISO 3166, ISO 4217, GeoNames, Unicode CLDR and Wikidata datasets (updated monthly) with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **<stat key="data.countries.total:int">281</stat> countries** (<stat key="data.countries.historic:int">31</stat> historic) sourced and merged from ISO 3166-1, ISO 3166-3, and GeoNames
- 🗺️ **<stat key="data.subdivisions.total:int">51,711</stat> subdivisions** sourced and merged from ISO 3166-2 and GeoNames
- 🏙️ **<stat key="data.cities.total:int">235,917</stat> cities** sourced from GeoNames cities500.txt
- 🌐 **<stat key="data.macroregions.total:int">34</stat> macroregions** (<stat key="data.macroregions.regions:int">5</stat> regions, <stat key="data.macroregions.subregions:int">23</stat> subregions, <stat key="data.macroregions.groupings:int">6</stat> groupings) sourced from Unicode CLDR, with every current country placed in them
- 💱 **<stat key="data.currencies.total:int">178</stat> currencies** and funds from ISO 4217, with each current country's legal tender from Unicode CLDR
- 🔍 **Typo-tolerant search**: with a typo in the query, the intended record ranks first for <stat key="bench.registries.countries.accuracy.top1_pct:pct">99.3%</stat> of countries, <stat key="bench.registries.subdivisions.accuracy.top1_pct:pct">85.5%</stat> of subdivisions and <stat key="bench.registries.cities.accuracy.top1_pct:pct">91.4%</stat> of cities
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

Each dataset is represented by its registry: `countries`, `subdivisions`, `cities`, `macroregions` and `currencies`, sharing a common query API.

| Registry | `get` | `lookup` | `filter` | `search` | Iteration |
|---|---|---|---|---|---|
| `countries` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `subdivisions` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `cities` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `macroregions` | ✓ | ✓ | | | ✓ |
| `currencies` | ✓ | ✓ | ✓ | ✓ | ✓ |

Lookups, filters and search ignore case and accents, so "sao paulo" finds São Paulo and "strasse" finds Straße.

### get

```python
country = localis.countries.get(1)
subdivision = localis.subdivisions.get(1)
city = localis.cities.get(1)
macroregion = localis.macroregions.get(1)
currency = localis.currencies.get(1)
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

```python
country = localis.countries.lookup("GB")
subdivision = localis.subdivisions.lookup("US-CA")
city = localis.cities.lookup(5128581)
macroregion = localis.macroregions.lookup("EU")
currency = localis.currencies.lookup("EUR")
```

**Returns:** the entity, or `None`

> ℹ️ `lookup()` matches identifiers only. Common abbreviations that aren't ISO codes, such as "UK" for the United Kingdom, are found by `filter(name=...)` and `search()`. M49 codes are zero-padded strings, so `macroregions.lookup("009")` finds Oceania and `lookup(9)` finds nothing.

### filter

Exact matches on any value a field indexes. Using multiple fields combines the conditions with a logical AND.

| Registry | Fields |
|---|---|
| `countries` | `name` (name, official name, common name or alias), `macroregion` (a region, subregion or grouping, by name or code), `currency` (by name or alpha-3) |
| `subdivisions` | `name` (name or alias), `type`, `country` (name, common name, alpha-2, alpha-3 or numeric), `admin_level` (0 = non-administrative groupings, 1 = states/provinces, 2 = counties/districts, 3 = divisions below those) |
| `cities` | `name`, `country` (name, common name, alpha-2 or alpha-3), `subdivision` (any subdivision in the city's chain, by name, ISO code or its suffix (`"CA"`), or GeoNames code) |
| `currencies` | `name` |

```python
localis.countries.filter(name="UK")  # aliases and abbreviations match too
localis.countries.filter(macroregion="Western Europe")
localis.countries.filter(currency="EUR")  # countries whose legal tender includes the euro
localis.subdivisions.filter(country="US", type="state")
localis.subdivisions.filter(admin_level=1, limit=10)
localis.cities.filter(country="US", subdivision="California", limit=20)

# Records with no value in a field
localis.subdivisions.filter(type=localis.MISSING)  # GeoNames-only subdivisions, which have no ISO type
localis.cities.filter(country="US", subdivision=localis.MISSING)  # US cities linked to no subdivision
localis.countries.filter(macroregion=localis.MISSING)  # historic countries placed in none (with include_historic set)
localis.countries.filter(currency=localis.MISSING)  # countries with no legal tender, such as Antarctica
```

Pass `localis.MISSING` to match records with no value in a field (`None` ignores the field). A field the registry doesn't have raises `TypeError`.

**Returns:** a list of entities sorted by name. `limit` defaults to every match.

### search

```python
for country, score in localis.countries.search("Germny", limit=5):
    print(f"{country.name}: {score:.2f}")
# Germany first, then weaker matches such as Guernsey

localis.subdivisions.search("Californa")
localis.cities.search("Springfeld, Illinois")  # context after the name narrows the match
localis.currencies.search("Swiss Frank")
```

A subdivision or city query can add context after the name: a subdivision's parent or country, or a city's first-level subdivision or country.

**Returns:** a list of `(entity, score)` pairs, best match first. Each score runs from 0 to 1, higher is better. `limit` defaults to 10.

### Iteration and len()

```python
for country in localis.countries:
    print(country.name)

total = len(localis.subdivisions)
```

> ℹ️ Historic countries are left out of `filter()`, `search()`, iteration and `len()` unless included (see [Historic Countries](#historic-countries)), and a population threshold narrows every cities query (see [Population Threshold](#population-threshold)).

---

## Entities

Results are typed dataclasses, listed field by field under each registry below. Each has `to_dict()` and `json()`, `str()` gives its JSON, and `key` is its stable reference (see [key](#key) below). A record nested in another, such as `subdivision.country`, `city.subdivisions`, `country.macroregions` or `country.currencies`, is its base form (`CountryBase`, `SubdivisionBase`, `MacroregionBase`, `CurrencyBase`), which keeps the fields marked Base in those tables.

```python
country = localis.countries.lookup("US")
country.to_dict()                # dict of every field
country.json()                   # the same, as a JSON string
localis.subdivisions.lookup("US-CA").country.alpha3  # "USA", from the nested CountryBase
```

### key

localis IDs are assigned in order each time the data is built. You can use them to carry a record from one query to the next within a process, but don't store them.

`key` extracts the entity's stable lookup identifier, which can be used to reliably reference the entity across different versions of the dataset.

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

Nested records have a `key` too, so `city.country.key` and `city.subdivisions[0].key` resolve the same way. A key changes only when its source recodes the place itself, such as ISO reassigning a subdivision's code, and a stored GeoNames code still resolves after the subdivision gains an ISO code.

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

`get()` and `lookup()` always resolve historic entries regardless of the toggle. ISO reused alpha-2/alpha-3/numeric codes across different withdrawn countries over time (e.g. `CS` was both Czechoslovakia and, decades later, Serbia and Montenegro), so `lookup()` only resolves a historic entry by its unique `alpha_4` withdrawal code, never by bare alpha-2/alpha-3/numeric:

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
| `aliases` | `tuple[str, ...]` | | alternate names from GeoNames and Wikidata | |
| `flag` | `str \| None` | `"🇺🇸"` | Unicode flag emoji | |
| `historic` | `HistoricInfo \| None` | `None` | set only for withdrawn ISO 3166-3 countries | |
| `macroregions` | `tuple[MacroregionBase, ...]` | (Americas, Northern America) | CLDR path, region then subregion; `()` for most historic countries | |
| `groupings` | `tuple[MacroregionBase, ...]` | (North America, United Nations) | CLDR groupings the country belongs to | |
| `currencies` | `tuple[CurrencyBase, ...]` | (US Dollar) | legal tender in use, per CLDR, in CLDR's order; `()` for historic countries | |

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
| `aliases` | `tuple[str, ...]` | | alternate names | |

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

`cities` is fully lazy-loaded: nothing is read from disk until first access. Call `set_population_threshold()` before that first access (before any `.get()`, `.lookup()`, `.filter()`, `.search()`, or `.force_cache()` call) so the registry only ever loads the narrowed dataset. Calling it after the cache or indexes are already built still works, but it invalidates them, so the next access rebuilds the caches from scratch at the new threshold.

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

Every ISO 4217 code ships, funds (`"CHE"`, `"BOV"`), precious metals (`"XAU"`) and special codes (`"XDR"`, `"XTS"`, `"XXX"`) included, as ISO publishes them. A country's `currencies` lists only its legal tender in use, per CLDR: <stat key="data.currencies.linked:int">153</stat> currencies are some current country's legal tender, and <stat key="data.currencies.multi_currency_countries:int">7</stat> countries have more than one, such as Panama's balboa and US dollar. Historic countries list none, since CLDR keys its currency data by alpha-2 codes ISO has since reused.

#### Currency Object

A ✓ under Base marks a field the nested `CurrencyBase` also has.

| Field | Type | Example (`"EUR"`) | Notes | Base |
|---|---|---|---|---|
| `id` | `int` | | localis ID, valid within this version | ✓ |
| `key` | `str` | `"EUR"` | stable reference to store, the alpha-3 | ✓ |
| `name` | `str` | `"Euro"` | ISO 4217 name, as published | ✓ |
| `alpha3` | `str` | `"EUR"` | | ✓ |
| `numeric` | `int \| None` | `978` | ISO 4217 numeric code | |

---

## Performance

### Caching

All registries and their indexes are lazy-loaded on first use, incurring a cold start cost on whichever call touches them first. Any registry's dataset and indexes can be pre-loaded with `.force_cache()` to avoid this during queries, or you can simply access the registry/method to trigger the lazy loading upfront.

> ℹ️ A registry's dataset also loads the datasets it references, if they aren't cached yet. Countries load macroregions and currencies, subdivisions load countries, and cities load subdivisions and countries. Only those datasets load, not their indexes. The subdivisions and cities tables below exclude them, so a cold first call on cities also pays for the subdivisions and countries datasets.

#### Countries (<stat key="data.countries.total:int">281</stat>)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | <stat key="footprint.registries.countries.dataset.time_ms:load">~1ms</stat> | <stat key="footprint.registries.countries.dataset.memory_bytes:size">268KB</stat> |
| Lookup index | <stat key="footprint.registries.countries.lookup_index.time_ms:load">< 1ms</stat> | <stat key="footprint.registries.countries.lookup_index.memory_bytes:size">41KB</stat> |
| Filter index | <stat key="footprint.registries.countries.filter_index.time_ms:load">~1ms</stat> | <stat key="footprint.registries.countries.filter_index.memory_bytes:size">158KB</stat> |
| Search index | <stat key="footprint.registries.countries.search_index.time_ms:load">~4ms</stat> | <stat key="footprint.registries.countries.search_index.memory_bytes:size">390KB</stat> |
| **Combined** | **<stat key="footprint.registries.countries.combined.time_ms:load">~7ms</stat>** | **<stat key="footprint.registries.countries.combined.memory_bytes:size">857KB</stat>** |

#### Subdivisions (<stat key="data.subdivisions.total:int">51,711</stat>)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | <stat key="footprint.registries.subdivisions.dataset.time_ms:load">~76ms</stat> | <stat key="footprint.registries.subdivisions.dataset.memory_bytes:size">14.2MB</stat> |
| Lookup index | <stat key="footprint.registries.subdivisions.lookup_index.time_ms:load">~15ms</stat> | <stat key="footprint.registries.subdivisions.lookup_index.memory_bytes:size">4.3MB</stat> |
| Filter index | <stat key="footprint.registries.subdivisions.filter_index.time_ms:load">~67ms</stat> | <stat key="footprint.registries.subdivisions.filter_index.memory_bytes:size">11.5MB</stat> |
| Search index | <stat key="footprint.registries.subdivisions.search_index.time_ms:load">~58ms</stat> | <stat key="footprint.registries.subdivisions.search_index.memory_bytes:size">11.8MB</stat> |
| **Combined** | **<stat key="footprint.registries.subdivisions.combined.time_ms:load">~216ms</stat>** | **<stat key="footprint.registries.subdivisions.combined.memory_bytes:size">41.8MB</stat>** |

#### Cities (<stat key="data.cities.total:int">235,917</stat>)


| Component | Load Time | Memory |
|---|---|---|
| Dataset | <stat key="footprint.registries.cities.dataset.time_ms:load">~338ms</stat> | <stat key="footprint.registries.cities.dataset.memory_bytes:size">28.1MB</stat> |
| Lookup index | <stat key="footprint.registries.cities.lookup_index.time_ms:load">~75ms</stat> | <stat key="footprint.registries.cities.lookup_index.memory_bytes:size">1.8MB</stat> |
| Filter index | <stat key="footprint.registries.cities.filter_index.time_ms:load">~287ms</stat> | <stat key="footprint.registries.cities.filter_index.memory_bytes:size">49.1MB</stat> |
| Search index | <stat key="footprint.registries.cities.search_index.time_ms:load">~196ms</stat> | <stat key="footprint.registries.cities.search_index.memory_bytes:size">41.9MB</stat> |
| **Combined** | **<stat key="footprint.registries.cities.combined.time_ms:load">~896ms</stat>** | **<stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat>** |

> ⚠️ **Memory-intensive.** Fully caching cities and its indexes adds <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat> of memory. Calling `localis.cities.force_cache()` loads all of it upfront. You can call `cities.set_population_threshold(n)` before first access as a lever to control the memory footprint.

At a threshold of <stat key="data.cities.threshold:int">15,000</stat>, cities drops from <stat key="data.cities.total:int">235,917</stat> to <stat key="data.cities.above_threshold:int">34,171</stat> and memory drops from <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat> to <stat key="footprint.cities_threshold.memory_bytes:size">28.4MB</stat>.

**Full Cache**: <stat key="footprint.full_cache.time_ms:load">~1.12s</stat> load time, <stat key="footprint.full_cache.memory_bytes:size">163.6MB</stat> memory for all datasets and indexes

### Search Benchmarks

`get()` and `lookup()` are O(1) hash lookups and `filter()` reads precomputed index sets, so all three return in microseconds on warm caches.

| Registry | Latency (p50 / p95) | Accuracy (top 10) | Top Result |
|---|---|---|---|
| Countries | <stat key="bench.registries.countries.search.p50_ms:latency">1.34ms</stat> / <stat key="bench.registries.countries.search.p95_ms:latency">4.42ms</stat> | <stat key="bench.registries.countries.accuracy.success_pct:pct">100.0%</stat> | <stat key="bench.registries.countries.accuracy.top1_pct:pct">99.3%</stat> |
| Subdivisions | <stat key="bench.registries.subdivisions.search.p50_ms:latency">2.8ms</stat> / <stat key="bench.registries.subdivisions.search.p95_ms:latency">5.15ms</stat> | <stat key="bench.registries.subdivisions.accuracy.success_pct:pct">97.3%</stat> | <stat key="bench.registries.subdivisions.accuracy.top1_pct:pct">85.5%</stat> |
| Cities | <stat key="bench.registries.cities.search.p50_ms:latency">6.79ms</stat> / <stat key="bench.registries.cities.search.p95_ms:latency">12.1ms</stat> | <stat key="bench.registries.cities.accuracy.success_pct:pct">98.4%</stat> | <stat key="bench.registries.cities.accuracy.top1_pct:pct">91.4%</stat> |

Accuracy tested on <stat key="bench.sample_size:int">5,000</stat> mangled-query samples per registry; cities' search additionally includes city + admin1 context. Load times, memory and latency are generated by `tests/analysis/footprint.py` and `tests/analysis/benchmarks.py`, last measured on <stat key="footprint.host.cpu">11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz</stat> with Python <stat key="footprint.host.python">3.14.7</stat>.

---

## Concurrency

Registries are safe to share across threads. `get()`, `lookup()`, `filter()`, `search()` and iteration only read shared data, and the first access that loads a dataset or index does so under the registry's lock, so threads reaching a cold registry together load it once.

> ⚠️ Two settings change shared state for every thread: `cities.set_population_threshold()` and `countries.set_include_historic()`. Configure them before the registry is shared between threads, never while other threads are querying it.

### Batch searching

localis doesn't parallelize batches for you, since the right approach depends on your Python build, memory budget and surrounding executor. On free-threaded Python (3.14t), a thread pool searches in parallel:

```python
from concurrent.futures import ThreadPoolExecutor
import localis

localis.cities.force_cache()  # load once, before the threads start
with ThreadPoolExecutor() as pool:
    results = list(pool.map(localis.cities.search, queries))
```

On a standard Python build the same code is correct but runs one search at a time, because the GIL lets only one thread run Python code at once. To search in parallel there, use processes. Each worker loads its own copy of the data (up to <stat key="footprint.registries.cities.combined.memory_bytes:size">121.0MB</stat> for cities), so apply any settings in the worker's initializer, and search through a module-level function, since a registry itself can't be sent to a process:

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

Names ship in Latin script.

[`docs/methodology.md`](docs/methodology.md) is a complete, falsifiable account of how each dataset is built: the rules that combine these sources, how the results were validated, and where they are known to be wrong. [`unmerged_subdivisions.md`](docs/unmerged_subdivisions.md) lists every ISO subdivision currently without a GeoNames counterpart, regenerated on every ingest run.

### Data licensing

The shipped data is derived from these sources, modified by localis's ingest pipeline, and remains under their licenses: ISO 3166 and ISO 4217 data via iso-codes (LGPL-2.1-or-later), GeoNames (CC BY 4.0), Unicode CLDR (Unicode License v3) and Wikidata (CC0). [`src/localis/data/NOTICE`](src/localis/data/NOTICE), which ships with the data, attributes each source, and the full license texts are in [`LICENSES/`](LICENSES) and in the wheel's metadata. If you redistribute the data, keep that notice and those licenses with it.

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