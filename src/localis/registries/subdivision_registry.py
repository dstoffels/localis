from localis.models import SubdivisionModel
from localis.registries import Registry, CountryRegistry
from localis.indexes import FilterIndex, SearchEngine
import csv


class SubdivisionRegistry(Registry[SubdivisionModel]):
    DATA_PATH = Registry.DATA_PATH / "subdivisions"
    DATAFILE = "subdivisions.json.gz"
    MODEL_CLS = SubdivisionModel

    def __init__(self, countries: CountryRegistry, **kwargs):
        self._countries = countries
        super().__init__(**kwargs)

    # def load(self):
    #     self._cache = {}
    #     sub_groups: list[tuple[int, list[str]]] = []

    #     filepath = self.DATA_PATH / self.DATAFILE
    #     if not filepath.exists():
    #         raise FileNotFoundError(f"Data file not found: {filepath}")

    #     try:
    #         with open(filepath, "r", encoding="utf-8") as f:
    #             reader = csv.reader(f, delimiter="\t")
    #             next(reader)
    #             for id, row in enumerate(reader, 1):
    #                 sub_groups.append((id, row))
    #     except Exception as e:
    #         raise RuntimeError(f"Error loading subdivisions data: {e}") from e

    #     PARENT_ID_INDEX = 5

    #     # We need to sort the subdivision rows by parent_id before parsing so the parent subdivisions are already cached when their children need to reference them.
    #     sub_groups.sort(key=lambda r: r[1][PARENT_ID_INDEX])

    #     for id, row in sub_groups:
    #         self._parse_row(id, row)

    def _parse_row(self, id: int, row: list[str]):
        (
            name,
            aliases,
            geonames_code,
            iso_code,
            type,
            parent_id,  # index 5
            country_id,
            search_tokens,
        ) = row

        subdivision = SubdivisionModel(
            id=id,
            name=name,
            aliases=[alt for alt in aliases.split("|") if alt],
            geonames_code=geonames_code or None,
            iso_code=iso_code or None,
            type=type or None,
            admin_level=1 if not parent_id else 2,
            parent=self.cache.get(int(parent_id)) if parent_id else None,
            country=self._countries.cache.get(int(country_id)),
        )

        subdivision.search_tokens = search_tokens

        self._cache[id] = subdivision

    def get(self, identifier) -> SubdivisionModel | None:
        """Get a subdivision by its id, iso_code, or geonames_code."""
        return super().get(identifier)

    def load_filters(self):
        self._filter_index = FilterIndex(
            cache=self.cache, filter_fields=self.MODEL_CLS.FILTER_FIELDS
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
        self._search_index = SearchEngine(
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
