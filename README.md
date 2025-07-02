
# piecountry

`piecountry` is a Python package providing fast, easy access to ISO country and subdivision data with exact and fuzzy search capabilities. A better pycountry.

## Overview

- Lookup of countries by ISO alpha-2, alpha-3 codes, numeric codes, or country name.
- Fuzzy searching on country and subdivision names and codes.
- Lookup and filtering of subdivisions (states, provinces, regions) by name, ISO codes, and country.
- Retrieval of subdivision types per country.
- Support for common informal country code aliases (e.g., "uk" maps to "gb").

All functionality is exposed through:

- `piecountry.countries`
- `piecountry.subdivisions`

---

## Installation

```bash
pip install piecountry
```

---

## Usage

### Countries API

```python
import piecountry

# Exact lookup by alpha2, alpha3, numeric code, or country name
country = piecountry.countries.get("GB")          # United Kingdom
country = piecountry.countries.get("uk")          # United Kingdom (alias)
country = piecountry.countries.get("United Kingdom")
country = piecountry.countries.get(826)           # Numeric code for UK

# Fuzzy search returns list of (Country, similarity_score)
results = piecountry.countries.search("cananda")  # Will match "Canada"
for country, score in results:
    print(country.name, score)
```

### Subdivisions API

```python
import piecountry

# Exact lookup by subdivision name, ISO code, or alpha2 code
subdivision = piecountry.subdivisions.get("California")

# Fuzzy search for subdivisions
results = piecountry.subdivisions.search("calif")
for subdivision, score in results:
    print(subdivision.name, score)

# List all subdivisions in a country by country name or alpha2 code
us_subdivisions = piecountry.subdivisions.by_country("United States")
gb_subdivisions = piecountry.subdivisions.by_country_code("GB")

# Get all subdivision types within a country (e.g., "state", "province")
types = piecountry.subdivisions.get_types("GB")
print(types)
```

---

## API Reference

### `piecountry.countries`

- `get(identifier: str | int) -> Optional[Country]`  
  Retrieve a country by ISO alpha-2 code, alpha-3 code, numeric code, or full name (case-insensitive).  
  Supports common aliases like `"uk"` → `"gb"`.

- `search(query: str, limit: int = 5) -> list[tuple[Country, float]]`  
  Perform a fuzzy search on country names and codes. Returns a list of tuples `(Country, similarity_score)` sorted by score descending.

---

### `piecountry.subdivisions`

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

This site or product includes Ipregistry ISO 3166 data available from https://ipregistry.co."