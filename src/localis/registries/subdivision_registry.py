from typing import Mapping, cast
from localis.entities import Subdivision
from localis.views import CountryView, SubdivisionView
from localis.registries import Registry, CountryRegistry


class SubdivisionRegistry(Registry[Subdivision]):
    REGISTRY_NAME = "subdivisions"

    def __init__(self, countries: CountryRegistry, **kwargs):
        self._countries = countries
        super().__init__(**kwargs)

    def build_cache(self) -> Mapping[int, SubdivisionView]:
        country_views = cast(Mapping[int, CountryView], self._countries._cache)
        return SubdivisionView.load(self._data_filepath, country_views)

    def lookup(self, identifier: str | int) -> Subdivision | None:
        """Get a subdivision by its id, iso_code, or geonames_code."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name: str | None = None,
        limit: int | None = None,
        type: str | None = None,
        admin_level: int | None = None,
        country: str | None = None,
        **kwargs,
    ) -> list[Subdivision]:
        """Filter subdivisions by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs = {
            "type": type,
            "admin_level": admin_level,
            "country": country,
        }

        return super().filter(name=name, limit=limit, **kwargs)

    def search(
        self, query: str, limit: int = 10, **kwargs
    ) -> list[tuple[Subdivision, float]]:
        """Fuzzy search for subdivisions by name, aliases, parent name, or country name"""
        return super().search(query, limit, **kwargs)


# singleton
from localis.registries.country_registry import countries

subdivisions = SubdivisionRegistry(countries=countries)
