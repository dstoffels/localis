from localis.models import CityModel
from localis.registries import Registry, CountryRegistry, SubdivisionRegistry
from localis.indexes.filter_index import FilterIndex
from collections import defaultdict


class CityRegistry(Registry[CityModel]):
    DATA_PATH = Registry.DATA_PATH / "cities"
    DATAFILE = "cities.json.gz"
    MODEL_CLS = CityModel

    def __init__(
        self, countries: CountryRegistry, subdivisions: SubdivisionRegistry, **kwargs
    ):
        self._countries = countries
        self._subdivisions = subdivisions
        super().__init__(**kwargs)

    def _parse_row(self, id: int, row: list[str]):
        name, admin1_id, admin2_id, country_id, population, lat, lng, search_tokens = (
            row
        )
        admin1 = self._subdivisions.cache.get(int(admin1_id)) if admin1_id else None
        admin2 = self._subdivisions.cache.get(int(admin2_id)) if admin2_id else None
        country = self._countries.cache.get(int(country_id)) if country_id else None

        city = CityModel(
            id=id,
            name=name,
            admin1=admin1,
            admin2=admin2,
            country=country,
            population=int(population),
            lat=float(lat),
            lng=float(lng),
        )
        city.search_tokens = search_tokens
        self._cache[id] = city

    def get(self, identifier) -> CityModel | None:
        """Get a city by its id"""
        return super().get(identifier)

    def load_filters(self):
        self._filter_index = FilterIndex(
            cache=self.cache, filter_fields=self.MODEL_CLS.FILTER_FIELDS
        )

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
