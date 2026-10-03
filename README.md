# localis

Fast, offline access to comprehensive data for **countries**, **subdivisions**, **cities** and the **macroregions** countries sit in. Built on ISO 3166, GeoNames and Unicode CLDR datasets (updated monthly) with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **<!-- stat:data.countries.total:int -->281<!-- /stat --> countries** (<!-- stat:data.countries.historic:int -->31<!-- /stat --> historic) sourced and merged from ISO 3166-1, ISO 3166-3, and GeoNames
- 🗺️ **<!-- stat:data.subdivisions.total:int -->51,711<!-- /stat --> subdivisions** sourced and merged from ISO 3166-2 and GeoNames
- 🏙️ **<!-- stat:data.cities.total:int -->235,915<!-- /stat --> cities** sourced from GeoNames cities500.txt
- 🌐 **<!-- stat:data.macroregions.total:int -->34<!-- /stat --> macroregions** (<!-- stat:data.macroregions.regions:int -->5<!-- /stat --> regions, <!-- stat:data.macroregions.subregions:int -->23<!-- /stat --> subregions, <!-- stat:data.macroregions.groupings:int -->6<!-- /stat --> groupings) sourced from Unicode CLDR, with every current country placed in them
- 🔍 **Typo-tolerant search**: with a typo in the query, the intended record ranks first for <!-- stat:bench.registries.countries.accuracy.top1_pct:pct -->99.3%<!-- /stat --> of countries, <!-- stat:bench.registries.subdivisions.accuracy.top1_pct:pct -->85.0%<!-- /stat --> of subdivisions and <!-- stat:bench.registries.cities.accuracy.top1_pct:pct -->91.4%<!-- /stat --> of cities
- 📌 **Aliases** - support for colloquial, historic and alternate names

---

## Installation

```bash
pip install localis
```

---

## Quick Start

```python
import localis

# Countries
country = localis.countries.lookup("US")
print(country.name)  # "United States"

# Subdivisions
state = localis.subdivisions.lookup("US-CA")
print(state.name)  # "California"

# Fuzzy search
results = localis.countries.search("Austrlia")  # Typo-tolerant
print(results[0][0].name)  # "Australia"
```

---

## Countries

### Get

```python
import localis

# By localis ID
country = localis.countries.get(1)
```

**Returns:** `Country` object or `None`

### Lookup

```python
# By alpha-2 code
country = localis.countries.lookup("GB")

# By alpha-3 code
country = localis.countries.lookup("GBR")

# By numeric code
country = localis.countries.lookup(826)
```

**Returns:** `Country` object or `None`

### Filter

```python
# Exact name match (searches name, official_name, common_name, and aliases)
results = localis.countries.filter(name="Canada")

# General query across all fields
results = localis.countries.filter(name="United", limit=5)

# By macroregion: a region, subregion or grouping, by name or code
results = localis.countries.filter(macroregion="Western Europe")
results = localis.countries.filter(macroregion="EU")
```

**Returns:** `list[Country]`

### Fuzzy Search

```python
# Typo-tolerant search
results = localis.countries.search("Germny", limit=5)

for country, score in results:
    print(f"{country.name}: {score}")
# Output:
# Germany: 0.951
# Guernsey: 0.714
# ...
```

**Returns:** `list[tuple[Country, float]]` - sorted by similarity score

### Iteration

```python
# Iterate over all countries
for country in localis.countries:
    print(country.name)

# Get count
total = len(localis.countries)
```

### Historic Countries

ISO 3166-3 withdrawn countries (Czechoslovakia, Serbia and Montenegro, Netherlands Antilles, and others) are included in the dataset but excluded from `filter()`, `search()`, and iteration by default.

```python
localis.countries.include_historic   # False
len(list(localis.countries))         # 250

# Include historic entries
localis.countries.set_include_historic(True)
len(list(localis.countries))         # 281

localis.countries.set_include_historic(False)
```

The toggle applies to every thread using `localis.countries`, so set it before sharing the registry between threads (see Concurrency).

`get()` and `lookup()` always resolve historic entries regardless of the toggle. ISO reused alpha2/alpha3/numeric codes across different withdrawn countries over time (e.g. `CS` was both Czechoslovakia and, decades later, Serbia and Montenegro), so `lookup()` only resolves a historic entry by its unique `alpha_4` withdrawal code, never by bare alpha2/alpha3/numeric:

### Country Object

```python
country = localis.countries.lookup("US")

country.id            # Database ID
country.name          # "United States" - ISO 3166-1 name, as published
country.official_name # "United States of America" - ISO 3166-1 official name, or None where ISO has none
country.common_name   # None - common name from Debian iso-codes where it differs (e.g. "South Korea" for "Korea, Republic of"), otherwise None
country.alpha2        # "US"
country.alpha3        # "USA"
country.geonames_id   # 6252001
country.numeric       # 840
country.aliases       # tuple[str, ...] - Alternate names
country.flag          # "🇺🇸" - Unicode flag emoji
country.historic      # HistoricInfo | None - set only for withdrawn ISO 3166-3 countries
country.macroregions  # tuple[MacroregionBase, ...] - CLDR path, region then subregion: (Americas, Northern America); () for most historic countries
country.groupings     # tuple[MacroregionBase, ...] - CLDR groupings the country belongs to: (North America, United Nations)

country = localis.countries.lookup("CSHH")  # Czechoslovakia
country.historic.alpha_4            # "CSHH"
country.historic.withdrawal_date    # "1993-01-01"
country.historic.comment            # str | None

# Utility methods
country.to_dict()     # Convert to dictionary
country.json()        # Convert to JSON string
```

---

## Subdivisions

### Get by ID

```python
import localis

# By localis ID
subdivision = localis.subdivisions.get(1)
```

**Returns:** `Subdivision` object or `None`

### Lookup by identifier

```python
# By ISO code (country-subdivision)
subdivision = localis.subdivisions.lookup("US-CA")

# By GeoNames code
subdivision = localis.subdivisions.lookup("US.CA")
```

**Returns:** `Subdivision` object or `None`

### Filter

```python
# Exact name match
results = localis.subdivisions.filter(name="California")

# By subdivision type
results = localis.subdivisions.filter(type="state")

# By country
results = localis.subdivisions.filter(country="United States")

# By admin level (1 = states/provinces, 2 = counties/districts)
results = localis.subdivisions.filter(admin_level=1)

# Combine multiple filters (AND logic)
results = localis.subdivisions.filter(
    country="US",
    type="state",
    limit=10
)
```

**Returns:** `list[Subdivision]`

### Fuzzy Search

```python
results = localis.subdivisions.search("Californa", limit=3)

for subdivision, score in results:
    print(f"{subdivision.name}: {score}")
# California: 0.94
# Baja California: 0.8
# ...
```

**Returns:** `list[tuple[Subdivision, float]]`

### Subdivision Object

```python
subdivision = localis.subdivisions.lookup("US-CA")

subdivision.id              # Database ID
subdivision.name            # "California"
subdivision.geonames_code   # "US.CA"
subdivision.iso_code        # "US-CA"
subdivision.type            # "State"
subdivision.admin_level     # 1
subdivision.parent          # SubdivisionBase | None - Parent subdivision
subdivision.country         # CountryBase object
subdivision.aliases         # tuple[str, ...] - Alternate names

# Utility methods
subdivision.to_dict()       # Convert to dictionary
subdivision.json()          # Convert to JSON string
```

---

## Cities

### Get by ID

```python
import localis

# By localis ID
city = localis.cities.get(1)
```

**Returns:** `City` object or `None`

### Lookup by GeoNames id

```python
# By GeoNames ID
city = localis.cities.lookup(5128581)
```

**Returns:** `City` object or `None`

### Filter

```python
# Exact name match
results = localis.cities.filter(name="Los Angeles")

# By country name or alpha2/alpha 3 code
results = localis.cities.filter(country="United States", limit=10)

# By subdivision name or ISO/GeoNames code
results = localis.cities.filter(subdivision="California", limit=10)

# Combine filters (AND logic)
results = localis.cities.filter(
    country="US",
    subdivision="California",
    limit=20
)
```

**Returns:** `list[City]`

### Fuzzy Search

```python
results = localis.cities.search("Los Angelos", limit=5)

for city, score in results:
    print(f"{city.name}, {city.country.name}: {score}")
```

**Returns:** `list[tuple[City, float]]` - sorted by similarity score

### Population Threshold

```python
# Narrow the cache and all indexes to cities with population >= 15000
localis.cities.set_population_threshold(15000)

# Check the current threshold
localis.cities.population_threshold  # 15000

# Reset back to the full dataset
localis.cities.set_population_threshold(None)
```

`cities` is fully lazy-loaded, nothing is read from disk until first access. Call `set_population_threshold()` before that first access (before any `.get()`, `.lookup()`, `.filter()`, `.search()`, or `.force_cache()` call) so the registry only ever loads the narrowed dataset. Calling it after the cache or indexes are already built still works, but it invalidates them, so the next access rebuilds the caches from scratch at the new threshold. The threshold applies to every thread using `localis.cities`, so set it before sharing the registry between threads (see Concurrency).

**Returns:** `None`

### City Object

```python
city = localis.cities.lookup(5128581) # GeoNames ID

city.id              # Database ID
city.geonames_id     # 5128581
city.name            # "New York"
city.subdivisions    # list[SubdivisionBase] - ordered by admin_level ascending
city.country         # CountryBase object
city.population      # 8804190
city.lat             # 40.71427
city.lng             # -74.00597

# Utility methods
city.to_dict()       # Convert to dictionary
city.json()          # Convert to JSON string
```

---

## Macroregions

### Get

```python
# By localis ID
region = localis.macroregions.get(1)
```

**Returns:** `Macroregion` object or `None`

### Lookup

```python
# By code: M49 numeric codes are zero-padded strings, so lookup(9) finds nothing
oceania = localis.macroregions.lookup("009")
eu = localis.macroregions.lookup("EU")

# By name
western_europe = localis.macroregions.lookup("Western Europe")
```

**Returns:** `Macroregion` object or `None`

### Iteration

```python
for macroregion in localis.macroregions:
    print(macroregion.name)

total = len(localis.macroregions)
```

### Macroregion Object

```python
macroregion = localis.macroregions.lookup("155")

macroregion.id        # Database ID
macroregion.name      # "Western Europe" - CLDR English name
macroregion.code      # "155" - M49 numeric code as a string, or CLDR's letter code ("QO", "EU")
macroregion.type      # "region", "subregion" or "grouping"
macroregion.parent    # MacroregionBase | None - a subregion's region, or the region CLDR files a grouping under

# Utility methods
macroregion.to_dict() # Convert to dictionary
macroregion.json()    # Convert to JSON string
```

---

## Base Objects
Basic versions of country, subdivision and macroregion when nested.

### CountryBase Object


```python
nested_country = subdivision.country

nested_country.id
nested_country.name
nested_country.alpha2
nested_country.alpha3
nested_country.geonames_id
```

### SubdivisionBase Object

```python
nested_sub = city.subdivisions[0]

nested_sub.id
nested_sub.name
nested_sub.geonames_code
nested_sub.iso_code
nested_sub.type
nested_sub.admin_level
```

### MacroregionBase Object

```python
nested_macroregion = country.macroregions[0]

nested_macroregion.id
nested_macroregion.name
nested_macroregion.code
nested_macroregion.type
```

## Performance

### Caching

All registries and their indexes are lazy-loaded on first use, incurring a cold start cost on whichever call touches them first. Any registry's dataset and indexes can be pre-loaded with `.force_cache()` to avoid this during queries, or you can simply access the registry/method to trigger the lazy loading upfront.

A registry's dataset also loads the datasets it references, if they aren't cached yet. Countries load macroregions, subdivisions load countries, and cities load subdivisions and countries. Only those datasets load, not their indexes. The subdivisions and cities tables below exclude them, so a cold first call on cities also pays for the subdivisions and countries datasets.

#### Countries (<!-- stat:data.countries.total:int -->281<!-- /stat -->)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | <!-- stat:footprint.registries.countries.dataset.time_ms:load -->~1ms<!-- /stat --> | <!-- stat:footprint.registries.countries.dataset.memory_bytes:size -->183KB<!-- /stat --> |
| Lookup index | <!-- stat:footprint.registries.countries.lookup_index.time_ms:load -->< 1ms<!-- /stat --> | <!-- stat:footprint.registries.countries.lookup_index.memory_bytes:size -->32KB<!-- /stat --> |
| Filter index | <!-- stat:footprint.registries.countries.filter_index.time_ms:load -->< 1ms<!-- /stat --> | <!-- stat:footprint.registries.countries.filter_index.memory_bytes:size -->101KB<!-- /stat --> |
| Search index | <!-- stat:footprint.registries.countries.search_index.time_ms:load -->~2ms<!-- /stat --> | <!-- stat:footprint.registries.countries.search_index.memory_bytes:size -->339KB<!-- /stat --> |
| **Combined** | **<!-- stat:footprint.registries.countries.combined.time_ms:load -->~4ms<!-- /stat -->** | **<!-- stat:footprint.registries.countries.combined.memory_bytes:size -->656KB<!-- /stat -->** |

#### Subdivisions (<!-- stat:data.subdivisions.total:int -->51,711<!-- /stat -->)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | <!-- stat:footprint.registries.subdivisions.dataset.time_ms:load -->~71ms<!-- /stat --> | <!-- stat:footprint.registries.subdivisions.dataset.memory_bytes:size -->13.9MB<!-- /stat --> |
| Lookup index | <!-- stat:footprint.registries.subdivisions.lookup_index.time_ms:load -->~13ms<!-- /stat --> | <!-- stat:footprint.registries.subdivisions.lookup_index.memory_bytes:size -->3.5MB<!-- /stat --> |
| Filter index | <!-- stat:footprint.registries.subdivisions.filter_index.time_ms:load -->~107ms<!-- /stat --> | <!-- stat:footprint.registries.subdivisions.filter_index.memory_bytes:size -->11.7MB<!-- /stat --> |
| Search index | <!-- stat:footprint.registries.subdivisions.search_index.time_ms:load -->~56ms<!-- /stat --> | <!-- stat:footprint.registries.subdivisions.search_index.memory_bytes:size -->12.5MB<!-- /stat --> |
| **Combined** | **<!-- stat:footprint.registries.subdivisions.combined.time_ms:load -->~247ms<!-- /stat -->** | **<!-- stat:footprint.registries.subdivisions.combined.memory_bytes:size -->41.5MB<!-- /stat -->** |

#### Cities (<!-- stat:data.cities.total:int -->235,915<!-- /stat -->)

> ⚠️ **Memory-intensive.** Fully caching cities and its indexes adds <!-- stat:footprint.registries.cities.combined.memory_bytes:size -->104.5MB<!-- /stat --> of memory. Calling `localis.cities.force_cache()` loads all of it upfront. You can call `cities.set_population_threshold(n)` before first access as a lever to control the memory footprint.

| Component | Load Time | Memory |
|---|---|---|
| Dataset | <!-- stat:footprint.registries.cities.dataset.time_ms:load -->~332ms<!-- /stat --> | <!-- stat:footprint.registries.cities.dataset.memory_bytes:size -->24.5MB<!-- /stat --> |
| Lookup index | <!-- stat:footprint.registries.cities.lookup_index.time_ms:load -->~62ms<!-- /stat --> | <!-- stat:footprint.registries.cities.lookup_index.memory_bytes:size -->1.8MB<!-- /stat --> |
| Filter index | <!-- stat:footprint.registries.cities.filter_index.time_ms:load -->~613ms<!-- /stat --> | <!-- stat:footprint.registries.cities.filter_index.memory_bytes:size -->41.4MB<!-- /stat --> |
| Search index | <!-- stat:footprint.registries.cities.search_index.time_ms:load -->~158ms<!-- /stat --> | <!-- stat:footprint.registries.cities.search_index.memory_bytes:size -->36.7MB<!-- /stat --> |
| **Combined** | **<!-- stat:footprint.registries.cities.combined.time_ms:load -->~1.16s<!-- /stat -->** | **<!-- stat:footprint.registries.cities.combined.memory_bytes:size -->104.5MB<!-- /stat -->** |

At a threshold of <!-- stat:data.cities.threshold:int -->15,000<!-- /stat -->, cities drops from <!-- stat:data.cities.total:int -->235,915<!-- /stat --> to <!-- stat:data.cities.above_threshold:int -->34,171<!-- /stat --> and memory drops from <!-- stat:footprint.registries.cities.combined.memory_bytes:size -->104.5MB<!-- /stat --> to <!-- stat:footprint.cities_threshold.memory_bytes:size -->24.6MB<!-- /stat -->.

**Full Cache**: <!-- stat:footprint.full_cache.time_ms:load -->~1.43s<!-- /stat --> load time, <!-- stat:footprint.full_cache.memory_bytes:size -->146.6MB<!-- /stat --> memory for all datasets and indexes

### Benchmarks

Per-call query latency on warm caches, median (95th percentile), and fuzzy search accuracy on mangled/misspelled queries: how often the right entry appears in the top 10 results, and how often it's the top result.

| Registry | Get | Lookup | Filter | Search (avg/max) | Search Accuracy (top 10) | Top Result |
|---|---|---|---|---|---|---|
| Countries | <!-- stat:bench.registries.countries.get.p50_ms:latency -->0.0082ms<!-- /stat --> (<!-- stat:bench.registries.countries.get.p95_ms:latency -->0.0105ms<!-- /stat -->) | <!-- stat:bench.registries.countries.lookup.p50_ms:latency -->0.0116ms<!-- /stat --> (<!-- stat:bench.registries.countries.lookup.p95_ms:latency -->0.014ms<!-- /stat -->) | <!-- stat:bench.registries.countries.filter.p50_ms:latency -->0.0168ms<!-- /stat --> (<!-- stat:bench.registries.countries.filter.p95_ms:latency -->0.0206ms<!-- /stat -->) | <!-- stat:bench.registries.countries.search.p50_ms:latency -->1.91ms<!-- /stat --> (<!-- stat:bench.registries.countries.search.p95_ms:latency -->4.53ms<!-- /stat -->) | <!-- stat:bench.registries.countries.accuracy.success_pct:pct -->100.0%<!-- /stat --> | <!-- stat:bench.registries.countries.accuracy.top1_pct:pct -->99.3%<!-- /stat --> |
| Subdivisions | <!-- stat:bench.registries.subdivisions.get.p50_ms:latency -->0.0079ms<!-- /stat --> (<!-- stat:bench.registries.subdivisions.get.p95_ms:latency -->0.0094ms<!-- /stat -->) | <!-- stat:bench.registries.subdivisions.lookup.p50_ms:latency -->0.0132ms<!-- /stat --> (<!-- stat:bench.registries.subdivisions.lookup.p95_ms:latency -->0.0153ms<!-- /stat -->) | <!-- stat:bench.registries.subdivisions.filter.p50_ms:latency -->0.0176ms<!-- /stat --> (<!-- stat:bench.registries.subdivisions.filter.p95_ms:latency -->0.0317ms<!-- /stat -->) | <!-- stat:bench.registries.subdivisions.search.p50_ms:latency -->3.06ms<!-- /stat --> (<!-- stat:bench.registries.subdivisions.search.p95_ms:latency -->5.21ms<!-- /stat -->) | <!-- stat:bench.registries.subdivisions.accuracy.success_pct:pct -->97.0%<!-- /stat --> | <!-- stat:bench.registries.subdivisions.accuracy.top1_pct:pct -->85.0%<!-- /stat --> |
| Cities | <!-- stat:bench.registries.cities.get.p50_ms:latency -->0.0135ms<!-- /stat --> (<!-- stat:bench.registries.cities.get.p95_ms:latency -->0.017ms<!-- /stat -->) | <!-- stat:bench.registries.cities.lookup.p50_ms:latency -->0.0107ms<!-- /stat --> (<!-- stat:bench.registries.cities.lookup.p95_ms:latency -->0.013ms<!-- /stat -->) | <!-- stat:bench.registries.cities.filter.p50_ms:latency -->0.0225ms<!-- /stat --> (<!-- stat:bench.registries.cities.filter.p95_ms:latency -->0.0782ms<!-- /stat -->) | <!-- stat:bench.registries.cities.search.p50_ms:latency -->6.03ms<!-- /stat --> (<!-- stat:bench.registries.cities.search.p95_ms:latency -->10.6ms<!-- /stat -->) | <!-- stat:bench.registries.cities.accuracy.success_pct:pct -->98.6%<!-- /stat --> | <!-- stat:bench.registries.cities.accuracy.top1_pct:pct -->91.4%<!-- /stat --> |

Accuracy tested on <!-- stat:bench.sample_size:int -->5,000<!-- /stat --> mangled-query samples per registry; cities' search additionally includes city + admin1 context. Load times, memory and latency are generated by `tests/analysis/footprint.py` and `tests/analysis/benchmarks.py`, last measured on <!-- stat:footprint.host.cpu -->11th Gen Intel(R) Core(TM) i7-1165G7 @ 2.80GHz<!-- /stat --> with Python <!-- stat:footprint.host.python -->3.14.4<!-- /stat -->.

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
  - **Merged**: Additional subdivision aliases from GeoNames' `alternateNamesV2` dump (filtered by [Unicode CLDR](https://cldr.unicode.org/)'s official-language data per country)
- **Cities**
  - [GeoNames](https://www.geonames.org/) `cities500.txt` dataset
- **Macroregions**
  - [Unicode CLDR](https://cldr.unicode.org/) territory containment and English territory names

[`docs/methodology.md`](docs/methodology.md) is a complete, falsifiable account of how each dataset is built: the rules that combine these sources, how the results were validated, and where they are known to be wrong. [`unmerged_subdivisions.md`](docs/unmerged_subdivisions.md) lists every ISO subdivision currently without a GeoNames counterpart, regenerated on every ingest run.

### Concurrency
Registries are safe to share across threads. `get()`, `lookup()`, `filter()`, `search()` and iteration only read shared data, and the first access that loads a dataset or index does so under the registry's lock, so threads reaching a cold registry together load it once.

Two settings change shared state for every thread: `cities.set_population_threshold()` and `countries.set_include_historic()`. Configure them before the registry is shared between threads, never while other threads are querying it.

#### Batch searching

localis doesn't parallelize batches for you, since the right approach depends on your Python build, memory budget and surrounding executor. On free-threaded Python (3.14t), a thread pool searches in parallel:

```python
from concurrent.futures import ThreadPoolExecutor
import localis

localis.cities.force_cache()  # load once, before the threads start
with ThreadPoolExecutor() as pool:
    results = list(pool.map(localis.cities.search, queries))
```

On a standard Python build the same code is correct but runs one search at a time, because the GIL lets only one thread run Python code at once. To search in parallel there, use processes. Each worker loads its own copy of the data (up to <!-- stat:footprint.registries.cities.combined.memory_bytes:size -->104.5MB<!-- /stat --> for cities), so apply any settings in the worker's initializer, and search through a module-level function, since a registry itself can't be sent to a process:

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


### Data licensing

The shipped data is derived from these sources and remains subject to their licenses: ISO 3166 data via iso-codes (LGPL-2.1-or-later), GeoNames (CC BY 4.0), Wikidata (CC0), and Unicode CLDR (Unicode License v3).

---

## Requirements

- Python 3.11+
- `rapidfuzz` - Fast fuzzy string matching
- `unidecode` - Unicode text normalization

---

## License

Code: MIT. Data: subject to its sources' licenses, listed under [Data licensing](#data-licensing).

---

## Why localis
localis began with some database cleanup. I found myself writing mountains of bespoke code to parse inconsistent, dirty data with pycountry, GeoNames and Wikidata to name a few (Google Places was not in the budget). When the pipeline was complete and the data cleaned, I realized this mountain of code could be useful for others who might need a reliable offline geo-data solution, so here we are! I hope you find it useful and please don't hesitate to contribute or report any issues.

---

## Contributing
[Pull requests welcome](https://github.com/dstoffels/localis)
[Report issues](https://github.com/dstoffels/localis/issues)

Support this project: 
- [GitHub Sponsors](https://github.com/sponsors/dstoffels)
- [PayPal](https://www.paypal.biz/danOstoffels)
