from localis.models import CityModel, CityView, City
from localis.registries import Registry, CountryRegistry, SubdivisionRegistry


class CityRegistry(Registry[City]):
    REGISTRY_NAME = "cities"
    LAZY_LOAD = True
    _MODEL_CLS = CityModel

    def __init__(
        self, countries: CountryRegistry, subdivisions: SubdivisionRegistry, **kwargs
    ):
        self._countries = countries
        self._subdivisions = subdivisions
        super().__init__(**kwargs)

    def build_cache(self) -> dict[int, CityView]:
        return CityView.load(
            self._data_filepath, self._countries._cache, self._subdivisions._cache
        )

    def get(self, id: int) -> City | None:
        """Get a city by its localis ID."""
        return super().get(id)

    def lookup(self, identifier: str | int) -> City | None:
        """Get a city by its GeoNames ID."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name: str | None = None,
        limit: int | None = None,
        subdivision: str | None = None,
        country: str | None = None,
        # population__lt: int = None, # TODO: to be implemented
        # population__gt: int = None, # TODO: to be implemented
        **kwargs,
    ) -> list[City]:
        """Filter cities by name, subdivision (name, iso/geonames code) or country (name, alpha2, alpha3) with additional filtering by population. Multiple filters use logical AND."""
        kwargs = {
            "subdivision": subdivision,
            "country": country,
        }
        results = super().filter(name=name, limit=limit, **kwargs)
        return results

    def search(
        self, query: str, limit: int = 10, population_sort: bool = False, **kwargs
    ) -> list[tuple[City, float]]:
        """Search cities by name, subdivision (name, iso/geonames code), or country (name, alpha2, alpha3). Can optionally sort by population, which is great for autocompletes."""
        results: list[tuple[City, float]] = super().search(
            query=query, limit=limit, **kwargs
        )
        if population_sort:
            results.sort(key=lambda x: x[0].population, reverse=True)
        return results


# ----------- SINGLETON ----------- #
from localis.registries.country_registry import countries
from localis.registries.subdivision_registry import subdivisions

cities: CityRegistry = CityRegistry(countries=countries, subdivisions=subdivisions)
