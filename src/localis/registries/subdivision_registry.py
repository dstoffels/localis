from localis.models import SubdivisionModel, SubdivisionView, Subdivision
from localis.registries import Registry, CountryRegistry


class SubdivisionRegistry(Registry[Subdivision]):
    REGISTRY_NAME = "subdivisions"
    _MODEL_CLS = SubdivisionModel

    def __init__(self, countries: CountryRegistry, **kwargs):
        self._countries = countries
        super().__init__(**kwargs)

    def build_cache(self) -> dict[int, SubdivisionView]:
        return SubdivisionView.load(self._data_filepath, self._countries._cache)

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

    def search(self, query, limit=10, **kwargs) -> list[tuple[SubdivisionModel, float]]:
        """Fuzzy search for subdivisions by name, aliases, parent name, or country name"""
        return super().search(query, limit, **kwargs)


# singleton
from localis.registries.country_registry import countries

subdivisions = SubdivisionRegistry(countries=countries)
