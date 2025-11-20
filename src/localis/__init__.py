from localis.registries import CountryRegistry, SubdivisionRegistry, CityRegistry
from localis.data import CountryModel, SubdivisionModel, CityModel
from localis.dtos import Country, Subdivision, City

countries = CountryRegistry(CountryModel)
"""The countries registry

- Registries are iterable. NOTE: caches all entries on first iterable access. 
- To manually trigger caching, access `localis.countries.cache` (property).
"""

subdivisions = SubdivisionRegistry(SubdivisionModel)
"""The subdivisions registry

- Registries are iterable. NOTE: caches all entries (51k entries, 30MB) on first iterable access. 
- To manually trigger caching, access `localis.subdivisions.cache` (property).
"""

cities = CityRegistry(CityModel)
"""The cities registry.

- Must be loaded before use: `localis.cities.load()` or via CLI `localis load cities`.
- WARNING: Loading this registry expands the database to ~250MB.
- Registries are iterable. WARNING: caches all entries (451k cities, 461MB) on first iterable access.
- To manually trigger caching, access `localis.cities.cache` (property).
"""
