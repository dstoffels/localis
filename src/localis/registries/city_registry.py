from typing import Mapping, cast
from localis.entities import City
from localis.utils.data import CacheFilterPredicate
from localis.views import CountryView, CityView, SubdivisionView
from localis.registries import Registry, CountryRegistry, SubdivisionRegistry


class CityRegistry(Registry[City]):
    REGISTRY_NAME = "cities"
    LAZY_LOAD = True

    def __init__(
        self, countries: CountryRegistry, subdivisions: SubdivisionRegistry, **kwargs
    ):
        self._population_threshold: int | None = None
        self._population_filter: CacheFilterPredicate | None = None

        self._countries = countries
        self._subdivisions = subdivisions
        super().__init__(**kwargs)

    def build_cache(self) -> Mapping[int, CityView]:
        country_views = cast(Mapping[int, CountryView], self._countries._cache)
        subdivision_views = cast(
            Mapping[int, SubdivisionView], self._subdivisions._cache
        )
        result = CityView.load(
            self._data_filepath,
            country_views,
            subdivision_views,
            self._population_filter,
        )
        if self._population_filter is not None:
            self._allowed_ids = set(result.keys())
        return result

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

    def set_population_threshold(self, threshold: int | None) -> None:
        self._population_threshold = threshold
        if threshold is not None:
            self._population_filter = lambda row: int(row[5]) >= threshold
        else:
            self._population_filter = None
            self._allowed_ids = None

        self.invalidate_cache()

    @property
    def population_threshold(self) -> int | None:
        return self._population_threshold


# ----------- SINGLETON ----------- #
from localis.registries.country_registry import countries
from localis.registries.subdivision_registry import subdivisions

cities: CityRegistry = CityRegistry(countries=countries, subdivisions=subdivisions)
