from villager.registries import CountryRegistry, SubdivisionRegistry, CityRegistry
from villager.db import CountryModel, SubdivisionModel, CityModel
from villager.db.dtos import Country, Subdivision, City

countries = CountryRegistry(CountryModel)
subdivisions = SubdivisionRegistry(SubdivisionModel)
cities = CityRegistry(CityModel)
