# localis

Fast, offline access to comprehensive data for **countries**, **subdivisions**, and **cities**. Built on ISO 3166 and GeoNames datasets (updated monthly) with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **281 countries** (31 historic) sourced and merged from ISO 3166-1, ISO 3166-3, and GeoNames
- 🗺️ **51,803 subdivisions** sourced and merged from ISO 3166-2 and GeoNames
- 🏙️ **235,914 cities** sourced from GeoNames cities500.txt
- 🔍 **Search Engine** for typo-tolerant lookups with 99%+ accuracy
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

## Countries API

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
# Exact name match (searches name, official_name, and aliases)
results = localis.countries.filter(name="Canada")

# General query across all fields
results = localis.countries.filter(name="United", limit=5)
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

ISO 3166-3 withdrawn countries (Czechoslovakia, Serbia and Montenegro, Netherlands Antilles, and 28 others) are included in the dataset but excluded from `filter()`, `search()`, and iteration by default.

```python
localis.countries.include_historic   # False
len(list(localis.countries))         # 250

# Include historic entries
localis.countries.set_include_historic(True)
len(list(localis.countries))         # 281

localis.countries.set_include_historic(False)
```

`get()` and `lookup()` always resolve historic entries regardless of the toggle. ISO reused alpha2/alpha3/numeric codes across different withdrawn countries over time (e.g. `CS` was both Czechoslovakia and, decades later, Serbia and Montenegro), so `lookup()` only resolves a historic entry by its unique `alpha_4` withdrawal code, never by bare alpha2/alpha3/numeric:

### Country Object

```python
country = localis.countries.lookup("US")

country.id            # Database ID
country.name          # "United States"
country.official_name # "United States of America"
country.alpha2        # "US"
country.alpha3        # "USA"
country.geonames_id   # 6252001
country.numeric       # 840
country.aliases       # list[str] - Alternate names
country.flag          # "🇺🇸" - Unicode flag emoji
country.historic      # HistoricInfo | None - set only for withdrawn ISO 3166-3 countries

country = localis.countries.lookup("CSHH")  # Czechoslovakia
country.historic.alpha_4            # "CSHH"
country.historic.withdrawal_date    # "1993-01-01"
country.historic.comment            # str | None

# Utility methods
country.to_dict()     # Convert to dictionary
country.json()        # Convert to JSON string
```

---

## Subdivisions API

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
subdivision.aliases         # list[str] - Alternate names

# Utility methods
subdivision.to_dict()       # Convert to dictionary
subdivision.json()          # Convert to JSON string
```

---

## Cities API

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

`cities` is fully lazy-loaded, nothing is read from disk until first access. Call `set_population_threshold()` before that first access (before any `.get()`, `.lookup()`, `.filter()`, `.search()`, or `.force_cache()` call) so the registry only ever loads the narrowed dataset. Calling it after the cache or indexes are already built still works, but it invalidates them, so the next access rebuilds the caches from scratch at the new threshold.

**Returns:** `None`

### City Object

```python
city = localis.cities.lookup(5128581) # GeoNames ID

city.id              # Database ID
city.geonames_id     # 5128581
city.name            # "New York"
city.subdivisions    # list[SubdivisionBase] - ordered by admin_level ascending
city.country         # CountryBase object
city.population      # 8175133
city.lat             # 40.71427
city.lng             # -74.00597

# Utility methods
city.to_dict()       # Convert to dictionary
city.json()          # Convert to JSON string
```

---

## Base Objects
Basic versions of country and subdivision when nested.

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

## Performance

### Caching

All registries and their indexes are lazy-loaded on first use, incurring a cold start cost on whichever call touches them first. Any registry's dataset and indexes can be pre-loaded with `.force_cache()` to avoid this during queries, or you can simply access the registry/method to trigger the lazy loading upfront.

#### Countries (281)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | ~1ms | ~400KB |
| Lookup index | < 1ms | ~0KB |
| Filter index | ~1ms | ~200KB |
| Search index | ~2ms | ~700KB |
| **Combined** | **~4ms** | **~1.4MB** |

#### Subdivisions (51,803)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | ~102ms | 27.0MB |
| Lookup index | ~14ms | 3.8MB |
| Filter index | ~124ms | 19.4MB |
| Search index | ~68ms | 11.4MB |
| **Combined** | **~309ms** | **61.6MB** |

#### Cities (235,914)

> ⚠️ **Memory-intensive.** Fully caching cities and its indexes adds 151.0MB of resident memory. Calling `localis.cities.force_cache()` loads all of it upfront. You can call `cities.set_population_threshold(n)` before first access as a lever to control the memory footprint.

| Component | Load Time | Memory |
|---|---|---|
| Dataset | ~460ms | 61.1MB |
| Lookup index | ~71ms | < 100KB |
| Filter index | ~620ms | 57.2MB |
| Search index | ~189ms | 32.7MB |
| **Combined** | **~1.34s** | **151.0MB** |

At a threshold of 15,000, cities drops from 235,914 to 34,167 and memory drops from 151.0MB to 31.5MB.

**Full Cache**: ~1.65s load time, 214.0MB memory for all datasets and indexes

**Concurrency:** It is recommended to call `.force_cache()` on all registries if they will be accessed from multiple threads to avoid potential race conditions during the first access of any lazy-loaded caches and indexes.

### Benchmarks

Per-call query latency, and fuzzy search accuracy on mangled/misspelled queries:

| Registry | Get | Lookup | Filter | Search | Search Accuracy |
|---|---|---|---|---|---|
| Countries | 0.0009ms | 0.0029ms | 0.0054ms | 1.27ms | 100% |
| Subdivisions | 0.002ms | 0.0059ms | 0.013ms | 3.28ms | 94% |
| Cities | 0.0043ms | 0.0046ms | 0.0166ms | 4.94ms | 99%+ |

Accuracy tested on 5,000 mangled-query samples per registry; cities' search additionally includes city + admin1 context.

---

## Data Sources
Data in this project is kept current monthly from the following sources:

- **Countries**
  - **Canonical**: [ISO 3166-1](https://www.iso.org/iso-3166-country-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [ISO 3166-3](https://www.iso.org/iso-3166-country-codes.html) withdrawn/historic country codes, also via Debian's iso-codes project
  - **Merged**: [GeoNames](https://www.geonames.org/) `countryInfo.txt`
  - **Merged**: Additional country aliases from a static [Wikidata](https://www.wikidata.org/) snapshot (not refreshed monthly)
- **Subdivisions**
  - **Canonical**: [ISO 3166-2](https://www.iso.org/iso-3166-country-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [GeoNames](https://www.geonames.org/) `admin1CodesASCII.txt` and `admin2Codes.txt`
  - **Merged**: [Wikidata](https://www.wikidata.org/) crosswalk (ISO 3166-2 code ↔ GeoNames id) for unambiguous resolution ahead of fuzzy matching
  - **Merged**: Additional subdivision aliases from GeoNames' `alternateNamesV2` dump (filtered by [Unicode CLDR](https://cldr.unicode.org/)'s official-language data per country)
- **Cities**
  - [GeoNames](https://www.geonames.org/) `cities500.txt` dataset

[`docs/methodology.md`](docs/methodology.md) is a complete, falsifiable account of how each dataset is built: the rules that combine these sources, how the results were validated, and where they are known to be wrong. [`unmerged_subdivisions.md`](docs/unmerged_subdivisions.md) lists every ISO subdivision currently without a GeoNames counterpart, regenerated on every ingest run.

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
