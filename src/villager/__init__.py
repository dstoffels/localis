from villager.registries import CountryRegistry, SubdivisionRegistry, CityRegistry
from villager.db import CountryModel, SubdivisionModel, CityModel
from villager.dtos import Country, Subdivision, City

countries = CountryRegistry(CountryModel)
"""The countries registry

- Registries are iterable. NOTE: caches all entries on first iterable access. 
- To manually trigger caching, access `villager.countries.cache` (property).
"""

subdivisions = SubdivisionRegistry(SubdivisionModel)
"""The subdivisions registry

- Registries are iterable. NOTE: caches all entries (51k entries, 30MB) on first iterable access. 
- To manually trigger caching, access `villager.subdivisions.cache` (property).
"""

cities = CityRegistry(CityModel)
"""The cities registry.

- Must be loaded before use: `villager.cities.load()` or via CLI `villager load cities`.
- WARNING: Loading this registry expands the database to ~200MB.
- Registries are iterable. WARNING: caches all entries (451k cities, 461MB) on first iterable access.
- To manually trigger caching, access `villager.cities.cache` (property).
"""
