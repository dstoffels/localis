from localis.models import CityModel
from localis.registries import Registry, CountryRegistry, SubdivisionRegistry
from localis.indexes.filter_index import FilterIndex
from collections import defaultdict


class CityRegistry(Registry[CityModel]):
    REGISTRY_NAME = "cities"
    _MODEL_CLS = CityModel

    def __init__(
        self, countries: CountryRegistry, subdivisions: SubdivisionRegistry, **kwargs
    ):
        self._countries = countries
        self._subdivisions = subdivisions
        super().__init__(**kwargs)

    def parse_row(self, id, row):
        return self._MODEL_CLS.from_row(
            id, row, self._countries._cache, self._subdivisions._cache
        )

    def get(self, id: int) -> CityModel | None:
        """Get by localis ID."""
        return super().get(id)

    def lookup(self, identifier) -> CityModel | None:
        """Get a city by its GeoNames ID."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name=None,
        limit: int = None,
        subdivision: str = None,
        country: str = None,
        # population__lt: int = None, # to be implemented
        # population__gt: int = None, # to be implemented
        **kwargs,
    ) -> list[CityModel]:
        """Filter cities by name, subdivision or country with additional filtering by population. Multiple filters use logical AND."""
        kwargs = {
            "subdivision": subdivision,
            "country": country,
        }
        results = super().filter(name=name, limit=limit, **kwargs)
        return results

    def search(
        self, query, limit=None, population_sort: bool = False, **kwargs
    ) -> list[tuple[CityModel, float]]:
        """Search cities by name, subdivision, or country. Can optionally sort by population, which is great for autocompletes."""
        results = super().search(query=query, limit=None, **kwargs)
        if population_sort:
            results.sort(key=lambda x: x[0].population, reverse=True)
        return results[:limit]


# ----------- SINGLETON ----------- #
from localis.registries.country_registry import countries
from localis.registries.subdivision_registry import subdivisions

cities: CityRegistry = CityRegistry(countries=countries, subdivisions=subdivisions)
