# localis

Fast, offline access to comprehensive geographic data for **countries**, **subdivisions**, and **cities**. Built on ISO 3166 and GeoNames datasets with support for exact lookups, filtering, and fuzzy search.

## Features

- 🌍 **249 countries** with ISO codes (alpha-2, alpha-3, numeric)
- 🗺️ **51,541 subdivisions** administrative levels 1 & 2
- 🏙️ **451,870 cities** sourced from GeoNames
- 🔍 **Search Engine** for typo-tolerant lookups with 90%+ accuracy
- ⚡ **Blazing fast** - caches in 1.2s, filters and lookups < 5ms, searches < 20ms
- 🔌 **Aliases** - support for colloquial, historic and alternate names

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
country = localis.countries.get(alpha2="US")
print(country.name)  # "United States"

# Subdivisions
state = localis.subdivisions.get(iso_code="US-CA")
print(state.name)  # "California"

# Fuzzy search
results = localis.countries.search("Austrlia")  # Typo-tolerant
print(results[0][0].name)  # "Australia"
```

---

## Countries API

### Get by identifier

```python
import localis

# By alpha-2 code
country = localis.countries.get(alpha2="GB")

# By alpha-3 code
country = localis.countries.get(alpha3="GBR")

# By numeric code
country = localis.countries.get(numeric=826)

# By database ID
country = localis.countries.get(id=1)
```

**Returns:** `Country` object or `None`

### Filter

```python
# Exact name match
results = localis.countries.filter(name="Canada")

# By official name
results = localis.countries.filter(official_name="United Kingdom")

# By alternative name
results = localis.countries.filter(alt_name="Holland")

# General query across all fields
results = localis.countries.filter(query="United", limit=5)
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

# Access by index
country = localis.countries[0]

# Get count
total = len(localis.countries)
```

### Country Object

```python
country = localis.countries.get(alpha2="US")

country.id            # Database ID
country.name          # "United States"
country.official_name # "United States of America"
country.alpha2        # "US"
country.alpha3        # "USA"
country.numeric       # 840
country.alt_names     # list[str] - Alternative names
country.flag          # "🇺🇸" - Unicode flag emoji

# Utility methods
country.to_dict()     # Convert to dictionary
country.json()        # Convert to JSON string
```

---

## Subdivisions API

### Get by identifier

```python
import localis

# By ISO code (country-subdivision)
subdivision = localis.subdivisions.get(iso_code="US-CA")

# By GeoNames code
subdivision = localis.subdivisions.get(geonames_code="US.CA")

# By database ID
subdivision = localis.subdivisions.get(id=1)
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

# By alternative name
results = localis.subdivisions.filter(alt_name="Cali")

# General query across all fields
results = localis.subdivisions.filter(query="New", limit=10)
```

**Returns:** `list[Subdivision]`

### Fuzzy Search

```python
results = localis.subdivisions.search("Californa", limit=3)

for subdivision, score in results:
    print(f"{subdivision.name}: {score}")
# California 0.92
# Baja California 0.763
```

**Returns:** `list[tuple[Subdivision, float]]`

### Get by Country

```python
# Get all subdivisions for a country
us_subdivisions = localis.subdivisions.for_country(alpha2="US")

# Filter by admin level (1 = states/provinces, 2 = counties/districts)
states = localis.subdivisions.for_country(alpha2="US", admin_level=1)
counties = localis.subdivisions.for_country(alpha2="US", admin_level=2)

# Can also use alpha3, numeric, or id
subdivisions = localis.subdivisions.for_country(alpha3="CAN")
subdivisions = localis.subdivisions.for_country(numeric=124)
```

**Returns:** `list[Subdivision]`

### Get Subdivision Types

```python
# Get all subdivision types for a country
types = localis.subdivisions.types_for_country(alpha2="GB")
print(types)  # ["Country", "Province", "District", ...]

# Filter by admin level
types = localis.subdivisions.types_for_country(alpha2="US", admin_level=1)
print(types)  # ["State", "District", "Outlying area"]
```

**Returns:** `list[str]`

### Subdivision Object

```python
subdivision = localis.subdivisions.get(iso_code="US-CA")

subdivision.id              # Database ID
subdivision.name            # "California"
subdivision.iso_code        # "US-CA"
subdivision.geonames_code   # "US.CA"
subdivision.type            # "State"
subdivision.country         # "United States"
subdivision.country_alpha2  # "US"
subdivision.country_alpha3  # "USA"
subdivision.admin_level     # 1
subdivision.parent_id       # int | None - Parent subdivision ID
subdivision.alt_names       # list[str] - Alternative names

# Utility methods
subdivision.to_dict()       # Convert to dictionary
subdivision.json()          # Convert to JSON string
```

---

## Cities API

### ⚠️ Important: Loading Cities Data

The cities dataset is **NOT included by default** due to its size (250MB+, 451,000 records).

**Load cities data:**

```bash
# Via CLI
localis loadcities

# Or in Python
import localis
localis.cities.load()
```

This will:
1. Copy the database to your project root as `localis.db`
2. Download the cities.tsv fixture
3. Load 451,000+ cities into the database
4. Add `localis.db` to your `.gitignore`
5. Create a `.localis.conf` file to track the database location

**Unload cities data:**

```bash
# Via CLI
localis unloadcities

# Or in Python
localis.cities.unload()
```

This removes the external database, config file, and reverts to the bundled read-only database.

### Get by identifier

```python
import localis

# By database ID
city = localis.cities.get(id=1)

# By GeoNames ID
city = localis.cities.get(geonames_id="5128581")
```

**Returns:** `City` object or `None`

### Filter

```python
# Exact name match
results = localis.cities.filter(name="Los Angeles")

# By country
results = localis.cities.filter(country="United States", limit=10)

# By subdivision (admin1)
results = localis.cities.filter(admin1="California", limit=10)

# By admin2 (county/district)
results = localis.cities.filter(admin2="Los Angeles County", limit=5)

# By alternative name
results = localis.cities.filter(alt_name="LA")

# General query across all fields
results = localis.cities.filter(query="San Diego", limit=20)
```

**Returns:** `list[City]`

### Fuzzy Search

```python
results = localis.cities.search("Los Angelos", limit=5)

for city, score in results:
    print(f"{city.name}, {city.country}: {score}")
```

**Returns:** `list[tuple[City, float]]` - sorted by population and similarity

### Get Cities by Country

```python
# Get all cities in a country
cities = localis.cities.for_country(alpha2="US")

# Filter by population
large_cities = localis.cities.for_country(
    alpha2="US",
    population__gt=1000000
)

small_cities = localis.cities.for_country(
    alpha2="US",
    population__lt=50000
)

# Can also use alpha3, numeric, or id
cities = localis.cities.for_country(alpha3="FRA")
cities = localis.cities.for_country(numeric=250)
```

**Returns:** `list[City]`

### Get Cities by Subdivision

```python
# Get all cities in a subdivision
cities = localis.cities.for_subdivision(iso_code="US-CA")

# Filter by population
cities = localis.cities.for_subdivision(
    geonames_code="US.CA",
    population__gt=500000
)

# Can also use id
cities = localis.cities.for_subdivision(id=123)
```

**Returns:** `list[City]`

### City Object

```python
city = localis.cities.get(geonames_id="5128581")

city.id              # Database ID
city.geonames_id     # 5128581
city.name            # "New York"
city.display_name    # str | None - Display name if different from name
city.subdivisions    # list[SubdivisionBasic] - Parent subdivisions
city.country         # "United States"
city.country_alpha2  # "US"
city.country_alpha3  # "USA"
city.population      # 8175133 | None
city.lat             # 40.71427
city.lng             # -74.00597
city.alt_names       # list[str] - Alternative names

# Utility methods
city.to_dict()       # Convert to dictionary
city.json()          # Convert to JSON string

# SubdivisionBasic structure
city.subdivisions[0].name            # "New York"
city.subdivisions[0].geonames_code   # "US.NY"
city.subdivisions[0].iso_code        # "US-NY"
city.subdivisions[0].admin_level     # 1
```

---

## CLI Commands

```bash

# Load cities dataset
localis loadcities

# Auto-confirm load
localis loadcities -y

# Load to custom directory
localis loadcities -p ./data

# Unload cities dataset
localis unloadcities
```

---

## Data Sources

- **Countries & Subdivisions**: [ISO 3166](https://www.iso.org/iso-3166-country-codes.html) data via [Ipregistry](https://ipregistry.co)
- **Cities**: [GeoNames](https://www.geonames.org/) `allCountries.txt` dataset (cities with population info, filtered by feature code)

---

## Performance Notes

- **Countries**:        All queries < 1ms.
- **Subdivisions**:     Cache time < 1s, search queries 8-13ms @ 95% accuract 
- **Cities**:           Fast SQLite queries with FTS5 full-text search (avg 48ms @ 89% accuracy)
- **Search Enginer**:   Diminishing token prefix truncation for FTS5 candidacy fed into rapidfuzz
- **Database size**:    
  - Base (countries/subdivisions): 16MB
  - With cities: 251MB

---

## Requirements

- Python 3.9+
- `rapidfuzz` required for search features
- `requests` required for loading cities dataset
---

## License

MIT

---

## Contributing

Issues and pull requests welcome at [github.com/dstoffels/localis](https://github.com/dstoffels/localis)
