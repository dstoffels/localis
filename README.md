# localis

Fast, offline access to comprehensive data for **countries**, **subdivisions**, and **cities**. Built on ISO 3166 and GeoNames datasets (updated monthly) with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **254 countries** sourced and merged from ISO 3166-1 and GeoNames
- 🗺️ **51,684 subdivisions** sourced and merged from ISO 3166-2 and GeoNames
- 🏙️ **235,895 cities** sourced from GeoNames cities500.txt
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

### Country Object

```python
country = localis.countries.lookup("US")

country.id            # Database ID
country.name          # "United States"
country.official_name # "United States of America"
country.alpha2        # "US"
country.alpha3        # "USA"
country.numeric       # 840
country.aliases       # list[str] - Alternate names
country.flag          # "🇺🇸" - Unicode flag emoji

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
localis.cities.get_population_threshold()  # 15000

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
city.admin1          # SubdivisionBase | None - Primary subdivision
city.admin2          # SubdivisionBase | None - Secondary subdivision
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
```

### SubdivisionBase Object

```python
nested_sub = city.admin1

nested_sub.id
nested_sub.name
nested_sub.geonames_code
nested_sub.iso_code
nested_sub.type
```

## Performance

### Caching

All registries (**Countries**, **Subdivisions**, **Cities**) and their indexes are lazy-loaded on first use, incurring a cold start cost on whichever call touches them first. Any registry's dataset and indexes can be pre-loaded with `.force_cache()` to avoid this during queries, or you can simply access the registry/method to trigger the lazy loading upfront.

#### Countries (254)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | ~1ms | 140KB |
| Lookup index | < 1ms | 24KB |
| Filter index | ~1ms | 180KB |
| Search index | ~7ms | 548KB |
| **Combined** | **~9ms** | **892KB** |

#### Subdivisions (51,684)
| Component | Load Time | Memory |
|---|---|---|
| Dataset | ~68ms | 21.6MB |
| Lookup index | ~12ms | 3.3MB |
| Filter index | ~89ms | 10.6MB |
| Search index | ~38ms | 9.0MB |
| **Combined** | **~207ms** | **44.6MB** |

#### Cities (235,895)

> ⚠️ **Memory-intensive.** Fully caching cities and its indexes adds 150.1MB of resident memory. Calling `localis.cities.force_cache()` loads all of it upfront. You can call `cities.set_population_threshold(n)` before first access as a lever to control the memory footprint.

| Component | Load Time | Memory |
|---|---|---|
| Dataset | ~395ms | 59.9MB |
| Lookup index | ~59ms | 4KB |
| Filter index | ~543ms | 56.7MB |
| Search index | ~144ms | 33.5MB |
| **Combined** | **~1.14s** | **150.1MB** |

At a threshold of 15,000 (the tier geonamescache ships as a separate bundled dataset), cities drops from 235,895 to 34,167 and memory drops from 150.1MB to 31.5MB.

**Full Cache**: ~1.4s load time, 195.6MB memory for all datasets and indexes

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
  - **Merged**: [Geonames](https://www.geonames.org/) `geonames_countries.txt`
  - **Merged**: Additional country aliases from Wikidata.
- **Subdivisions**
  - **Canonical**: [ISO 3166-2](https://www.iso.org/iso-3166-country-codes.html) data via [Debian's iso-codes project](https://salsa.debian.org/iso-codes-team/iso-codes)
  - **Merged**: [GeoNames](https://www.geonames.org/) `admin1CodesASCII.txt` and `admin2Codes.txt`
  - **Merged**: Additional subdivision aliases from [Ipregistry](https://ipregistry.co)
- **Cities**
  - [GeoNames](https://www.geonames.org/) `cities500.txt` dataset

Subdivisions in particular require reconciling two sources that disagree in nontrivial ways; see [`docs/methodology.md`](docs/methodology.md) for a complete, falsifiable account of how that reconciliation works, the thresholds and exceptions involved, and their evidentiary basis.

---

## Requirements

- Python 3.11+
- `rapidfuzz` - Fast fuzzy string matching
- `unidecode` - Unicode text normalization

---

## License

MIT

---

## Contributing

Pull requests welcome at [github.com/dstoffels/localis](https://github.com/dstoffels/localis)
Report issues: https://github.com/dstoffels/localis/issues