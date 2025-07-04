
# villager

`villager` is a Python package providing fast, easy access to ISO country and subdivision data with exact and fuzzy search capabilities. A better pycountry.

## Overview

- Lookup of countries by ISO alpha-2, alpha-3 codes, numeric codes, or country name.
- Fuzzy searching on country and subdivision names and codes.
- Lookup and filtering of subdivisions (states, provinces, regions) by name, ISO codes, and country.
- Retrieval of subdivision types per country.
- Support for common informal country code aliases (e.g., "uk" maps to "gb").

All functionality is exposed through:

- `villager.countries`
- `villager.subdivisions`

---

## Installation

```bash
pip install villager
```

---

## Usage

### Countries API

```python
import villager

# Exact lookup by alpha2, alpha3, numeric code, or country name (case-insentive)
country = villager.countries.get("GB")          # United Kingdom
country = villager.countries.get("uk")          # United Kingdom (alias)
country = villager.countries.get("United Kingdom")
country = villager.countries.get(826)           # Numeric code for UK

# Fuzzy search returns list of (Country, similarity_score)
results = villager.countries.search("cananda") 

print([(c.name, ratio) for c, ratio in results])
# [('Canada', 92.3076923076923), ('Tanzania', 66.66666666666667), ('Panama', 61.53846153846154), ('Rwanda', 61.53846153846154), ('Uganda', 61.53846153846154)]

```

### Subdivisions API

```python
import villager

# Exact lookup by subdivision name, ISO code, or alpha2 code (case-insentive)
subdivision = villager.subdivisions.get("California")

# Fuzzy search for subdivisions
results = villager.subdivisions.search("calif")
for subdivision, score in results:
    print(subdivision.name, score)

# List all subdivisions in a country by country name or alpha2 code
us_subdivisions = villager.subdivisions.by_country("United States")
gb_subdivisions = villager.subdivisions.by_country_code("GB")

# Get all subdivision types within a country (e.g., "state", "province")
types = villager.subdivisions.get_types("GB")
print(types)
```

---

## API Reference

### `villager.countries`

- `get(identifier: str | int) -> Optional[Country]`  
  Retrieve a country by ISO alpha-2 code, alpha-3 code, numeric code, or full name (case-insensitive).  
  Supports common aliases like `"uk"` → `"gb"`.

- `search(query: str, limit: int = 5) -> list[tuple[Country, float]]`  
  Perform a fuzzy search on country names and codes. Returns a list of tuples `(Country, similarity_score)` sorted by score descending.

---

### `villager.subdivisions`

- `get(identifier: str) -> Optional[Subdivision]`  
  Retrieve a subdivision by name, ISO code, or alpha2 code (case-insensitive).

- `search(query: str, limit: int = 5) -> list[tuple[Subdivision, float]]`  
  Fuzzy search subdivisions by name or codes.

- `by_country(name: str) -> list[Subdivision]`  
  Get all subdivisions within a country by full country name.

- `by_country_code(code: str) -> list[Subdivision]`  
  Get all subdivisions within a country by ISO alpha2 code.

- `get_types(code: str) -> list[str]`  
  List all subdivision types (e.g., "state", "province") within a given country code.

villager includes Ipregistry ISO 3166 data available from https://ipregistry.co."