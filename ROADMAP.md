# Roadmap

Features planned for future versions of localis. Nothing here is a commitment, and items can change or be dropped. If something matters to you, or is missing, [open an issue](https://github.com/dstoffels/localis/issues).

## 3.x

- **Translations**: names in other languages for every record, shown and matched, such as `localis.locale("de").countries.lookup("Deutschland")`.
- **Free-threaded Python**: support for 3.14t, with a batch search API.
- **City aliases**: English alternate names for larger cities, so "New York" finds New York City.
- **Nearby cities**: cities within a distance of a point.
- **Autocomplete** for registries.
- **Population ranges** on cities, such as `population__gt=...`.
- **Macroregion filters** on subdivisions and cities, such as `cities.filter(macroregion="Europe")`. Waiting on demand.
- **Subdivision match verification**: every ISO 3166-2 to GeoNames match independently verified, with coverage published in [methodology.md](docs/methodology.md).

## 4.0

- **Search result details**: each result says which name matched, how much of the query its context explained and whether it was exact, and each result set says how clearly the top result won and how many tied, so an ambiguous query like "springfield" can be detected.
- **Cities as a separate package**: a smaller core install, with cities as an optional extra. Waiting on demand.
