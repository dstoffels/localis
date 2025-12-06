from localis.models import SubdivisionModel, Subdivision
from localis.registries import Registry, CountryRegistry


class SubdivisionRegistry(Registry[Subdivision]):
    REGISTRY_NAME = "subdivisions"
    _MODEL_CLS = SubdivisionModel

    def __init__(self, countries: CountryRegistry, **kwargs):
        self._countries = countries
        super().__init__(**kwargs)

    def parse_row(self, id, row):
        return self._MODEL_CLS.from_row(id, row, self._countries._cache, self._cache)

    def lookup(self, identifier) -> SubdivisionModel | None:
        """Get a subdivision by its id, iso_code, or geonames_code."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name: str = None,
        limit: int = None,
        type: str = None,
        admin_level: int = None,
        country: str = None,
        **kwargs,
    ) -> list[SubdivisionModel]:
        """Filter subdivisions by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs = {
            "type": type,
            "admin_level": admin_level,
            "country": country,
        }

        return super().filter(name=name, limit=limit, **kwargs)

    def search(
        self, query, limit=None, **kwargs
    ) -> list[tuple[SubdivisionModel, float]]:
        """Fuzzy search for subdivisions by name, aliases, parent name, or country name"""
        return super().search(query, limit, **kwargs)


# singleton
from localis.registries.country_registry import countries

subdivisions = SubdivisionRegistry(countries=countries)
