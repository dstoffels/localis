from typing import Mapping, cast
from localis.entities import City
from localis.views import CountryView, CityView, SubdivisionView
from localis.registries import QueryableRegistry, CountryRegistry, SubdivisionRegistry


class CityRegistry(QueryableRegistry[City]):
    REGISTRY_NAME = "cities"
    NAME_FIELDS = ("name",)

    def __init__(self, countries: CountryRegistry, subdivisions: SubdivisionRegistry):
        self._population_threshold: int | None = None

        self._countries = countries
        self._subdivisions = subdivisions
        super().__init__()

    def build_cache(self) -> Mapping[int, CityView]:
        country_views = cast(Mapping[int, CountryView], self._countries._cache)
        subdivision_views = cast(
            Mapping[int, SubdivisionView], self._subdivisions._cache
        )
        return CityView.load(
            self._data_filepath,
            country_views,
            subdivision_views,
            self._row_filter,
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
        **kwargs,
    ) -> list[City]:
        """Filter cities by name, subdivision (name, iso/geonames code) or country (name, alpha2, alpha3). Multiple filters use logical AND."""
        kwargs.update(subdivision=subdivision, country=country)
        results = super().filter(name=name, limit=limit, **kwargs)
        return results

    def search(
        self, query: str, limit: int = 10, population_sort: bool = False
    ) -> list[tuple[City, float]]:
        """Search cities by name, subdivision (name, iso/geonames code), or country (name, alpha2, alpha3). Can optionally sort by population, which is great for autocompletes."""
        results: list[tuple[City, float]] = super().search(
            query=query, limit=limit
        )
        if population_sort:
            results.sort(key=lambda x: x[0].population, reverse=True)
        return results

    def set_population_threshold(self, threshold: int | None) -> None:
        # under the lock, so a thread building the cache never sees the filter change mid-build
        with self._lock:
            self._population_threshold = threshold
            if threshold is not None:
                self._row_filter = lambda row: int(row[4]) >= threshold
            else:
                self._row_filter = None
            self.invalidate_cache()

    @property
    def population_threshold(self) -> int | None:
        return self._population_threshold


# ----------- SINGLETON ----------- #
from localis.registries.country_registry import countries
from localis.registries.subdivision_registry import subdivisions

cities: CityRegistry = CityRegistry(countries=countries, subdivisions=subdivisions)
