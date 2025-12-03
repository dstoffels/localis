from localis.models import SubdivisionModel
from localis.registries import Registry, CountryRegistry
from localis.indexes import FilterIndex, SearchIndex
import csv


class SubdivisionRegistry(Registry[SubdivisionModel]):
    REGISTRY_NAME = "subdivisions"
    _MODEL_CLS = SubdivisionModel

    def __init__(self, countries: CountryRegistry, **kwargs):
        self._countries = countries
        super().__init__(**kwargs)

    def _resolve_model(self, id):
        row = self.cache.get(id)
        if not row:
            return None
        flat_model: SubdivisionModel = self._MODEL_CLS(*row)

        # Unresolved/flat models contain only IDs for dependencies from the row data.
        # We need to resolve those dependencies into full DTOs.
        flat_model.country = self._countries._resolve_model(flat_model.country)

        if flat_model.parent:
            flat_model.parent = self._resolve_model(flat_model.parent)

        # Collapse model to final DTO
        return flat_model.dto

    def lookup(self, identifier) -> SubdivisionModel | None:
        """Get a subdivision by its id, iso_code, or geonames_code."""
        return super().lookup(identifier)

    def load_filters(self):
        self._filter_index = FilterIndex(
            cache=self.cache, filter_fields=self._MODEL_CLS.FILTER_FIELDS
        )

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

    def load_search_index(self):
        self._search_index = SearchIndex(
            cache=self.cache, noise_threshold=0.5, penality_factor=0.1
        )

    def search(
        self, query, limit=None, **kwargs
    ) -> list[tuple[SubdivisionModel, float]]:
        """Fuzzy search for subdivisions by name, aliases, parent name, or country name"""
        return super().search(query, limit, **kwargs)


# singleton
from localis.registries.country_registry import countries

subdivisions = SubdivisionRegistry(countries=countries)
