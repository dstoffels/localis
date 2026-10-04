from typing import Mapping, cast
from localis.entities import Country
from localis.indexes import Missing
from localis.views import CountryView, MacroregionView
from localis.registries import QueryableRegistry, MacroregionRegistry
from localis.registries.registry import locked_cached_property


class CountryRegistry(QueryableRegistry[Country]):
    REGISTRY_NAME = "countries"
    NAME_FIELDS = ("name", "official_name", "common_name", "aliases")
    _CACHED_ATTRS = QueryableRegistry._CACHED_ATTRS + ("_historic_ids",)

    def __init__(self, macroregions: MacroregionRegistry):
        self._include_historic = False
        self._macroregions = macroregions
        super().__init__()

    def build_cache(self) -> Mapping[int, CountryView]:
        macroregion_views = cast(Mapping[int, MacroregionView], self._macroregions._cache)
        return CountryView.load(self._data_filepath, macroregion_views)

    @locked_cached_property
    def _historic_ids(self) -> frozenset[int]:
        cache = cast(Mapping[int, CountryView], self._cache)
        return frozenset(id for id, view in cache.items() if view.historic)

    def _hidden_ids(self) -> frozenset[int]:
        return frozenset() if self._include_historic else self._historic_ids

    def get(self, id: int) -> Country | None:
        """Get a country by its localis ID. Resolves historic entries regardless of include_historic."""
        return super().get(id)

    def lookup(self, identifier: str | int) -> Country | None:
        """Get a country by its alpha2, alpha3, ISO numeric code (an int), or alpha_4 withdrawal code (historic entries); use .get() for the localis id. Resolves historic entries regardless of include_historic."""
        return super().lookup(identifier)

    def filter(
        self,
        *,
        name: str | None = None,
        limit: int | None = None,
        macroregion: str | Missing | None = None,
        **kwargs,
    ) -> list[Country]:
        """Filter countries by any of its names (name, official_name, common_name, or aliases) or a macroregion (region, subregion or grouping, by name or code, or MISSING for none). Excludes historic entries unless include_historic is set."""
        kwargs.update(macroregion=macroregion)
        return super().filter(name=name, limit=limit, **kwargs)

    def search(
        self, query: str, limit: int = 10
    ) -> list[tuple[Country, float]]:
        """Search countries by any of their names (name, official_name, common_name, or aliases). Excludes historic entries unless include_historic is set."""
        return super().search(query, limit)

    def set_include_historic(self, include: bool) -> None:
        self._include_historic = include

    @property
    def include_historic(self) -> bool:
        return self._include_historic


# --------- Singleton --------- #
from localis.registries.macroregion_registry import macroregions

countries = CountryRegistry(macroregions=macroregions)
