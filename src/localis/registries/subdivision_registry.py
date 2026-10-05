from typing import Mapping, cast
from localis.entities import Subdivision
from localis.indexes import Missing
from localis.views import CountryView, SubdivisionView
from localis.registries import QueryableRegistry, CountryRegistry


class SubdivisionRegistry(QueryableRegistry[Subdivision]):
    REGISTRY_NAME = "subdivisions"
    NAME_FIELDS = ("name", "aliases", "iso_suffix")

    def __init__(self, countries: CountryRegistry):
        self._countries = countries
        super().__init__()

    def _build_cache(self) -> Mapping[int, SubdivisionView]:
        country_views = cast(Mapping[int, CountryView], self._countries._cache)
        return SubdivisionView.load(self._data_filepath, country_views)

    def lookup(self, identifier: str | int) -> Subdivision | None:
        """Get a subdivision by its iso_code or geonames_code; use .get() for the localis id."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name: str | None = None,
        limit: int | None = None,
        type: str | Missing | None = None,
        admin_level: int | None = None,
        country: str | None = None,
    ) -> list[Subdivision]:
        """Filter subdivisions by name (name or alias), type, admin_level or country (name, alpha2 or alpha3); type=MISSING matches the GeoNames-only subdivisions, which have no type."""
        return self._filter(limit, name=name, type=type, admin_level=admin_level, country=country)

    def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Subdivision, float]]:
        """Search subdivisions by name, alias or ISO code suffix, with their parent and country names matched as context."""
        return super().search(query, limit)


# singleton
from localis.registries.country_registry import countries

subdivisions = SubdivisionRegistry(countries=countries)
