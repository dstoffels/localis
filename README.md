# localis

Fast, offline access to comprehensive data for **countries**, **subdivisions**, and **cities**. Built on ISO 3166 and GeoNames datasets with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **249 countries** with ISO codes (alpha-2, alpha-3, numeric)
- 🗺️ **51,541 subdivisions** administrative levels 1 & 2
- 🏙️ **451,792 cities** sourced from GeoNames
- 🔍 **Search Engine** for typo-tolerant lookups with 99%+ accuracy
- ⚡ **Blazing fast** - full dataset loads in 1.1s, lookups < 5ms, searches < 30ms
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

### Lookup by identifier

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

### City Object

```python
city = localis.cities.lookup(5128581) # GeoNames ID

city.id              # Database ID
city.geonames_id     # 5128581
city.name            # "New York"
city.admin1          # SubdivisionBase | None - Primary subdivision
city.admin2          # SubdivisionBase | None - Secondary subdivision
city.country         # CountryBase object
city.population      # 8175133 | None
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

### Load Times

All data is eager-loaded on import. Each registry method lazy loads its respective indexes on first use, incurring a *cold start* cost. Indexes can be pre-loaded via `load_all()` to avoid this during queries.

- **Full dataset eager load**: ~1.1s (all 503k+ entities)
- **Countries** (249): < 5ms for all indexes
- **Subdivisions** (51,541): ~350ms for all indexes
- **Cities** (451,792)
  - Lookup index: ~150ms
  - Filter index: ~1.1s
  - Search index: ~1.7s
- **Total load time**: ~4.3s for all datasets and indexes

**Note:** These are best-case timings on modern hardware. Actual load times may vary based on host system.

### Query Performance

- **Countries**: 
  - All queries < 2ms
- **Subdivisions**: 
  - Lookups < 1ms
  - Filters < 3ms
  - Searches ~3ms
- **Cities**: 
  - Lookups < 5ms
  - Filters ~5ms
  - Searches < 30ms

### Search Accuracy

Fuzzy search accuracy on mangled/misspelled queries:

- **Countries**: 100%
- **Subdivisions**: 94% (tested on 5,000 samples)
- **Cities**: 99%+ (tested on 5,000 samples with city + admin1 context)

---

## Data Sources

- **Countries**
  - [ISO 3166-1](https://www.iso.org/iso-3166-country-codes.html) data via [Ipregistry](https://ipregistry.co)
- **Subdivisions**
  - [ISO 3166-2](https://www.iso.org/iso-3166-country-codes.html) data via [Ipregistry](https://ipregistry.co)
  - [GeoNames](https://www.geonames.org/) `admin1CodesASCII.txt` and `admin2Codes.txt`
- **Cities**
  - [GeoNames](https://www.geonames.org/) `allCountries.txt` dataset (cities with population data, filtered by feature codes)
  - Feature Codes used for cities: PPL, PPLA, PPLA2, PPLA3, PPLA4, PPLA5, PPLC, PPLF, PPLL, PPLS, STLMT

---

## Requirements

- Python 3.9+
- `rapidfuzz` - Fast fuzzy string matching
- `unidecode` - Unicode text normalization

---

## License

MIT

---

## Contributing

Issues and pull requests welcome at [github.com/dstoffels/localis](https://github.com/dstoffels/localis)