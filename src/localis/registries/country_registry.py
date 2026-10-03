from typing import Iterator, Mapping, cast
from localis.entities import Country
from localis.views import CountryView, MacroregionView
from localis.registries import QueryableRegistry, MacroregionRegistry


class CountryRegistry(QueryableRegistry[Country]):
    REGISTRY_NAME = "countries"
    NAME_FIELDS = ("name", "official_name", "common_name", "aliases")

    def __init__(self, macroregions: MacroregionRegistry, **kwargs):
        self._include_historic = False
        self._macroregions = macroregions
        super().__init__(**kwargs)

    def build_cache(self) -> Mapping[int, CountryView]:
        macroregion_views = cast(Mapping[int, MacroregionView], self._macroregions._cache)
        return CountryView.load(self._data_filepath, macroregion_views)

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
        macroregion: str | None = None,
        **kwargs,
    ) -> list[Country]:
        """Filter countries by any of its names (name, official_name, common_name, or aliases) or a macroregion (region, subregion or grouping, by name or code). Excludes historic entries unless include_historic is set."""
        kwargs.update(macroregion=macroregion)
        results = super().filter(name=name, limit=None, **kwargs)
        if not self._include_historic:
            results = [c for c in results if not c.historic]
        return results[:limit] if limit is not None else results

    def search(
        self, query: str, limit: int = 10, **kwargs
    ) -> list[tuple[Country, float]]:
        """Search countries by any of its names (name, official_name, or aliases). Excludes historic entries unless include_historic is set."""
        if self._include_historic:
            return super().search(query, limit, **kwargs)

        # over-fetch so excluding historic entries post-hoc can't under-return fewer than `limit` matches
        cache = cast(Mapping[int, CountryView], self._cache)
        historic_count = sum(1 for v in cache.values() if v.historic)
        results = super().search(query, limit + historic_count, **kwargs)
        return [(c, score) for c, score in results if not c.historic][:limit]

    def __iter__(self) -> Iterator[Country]:
        for c in super().__iter__():
            if self._include_historic or not c.historic:
                yield c

    def set_include_historic(self, include: bool) -> None:
        self._include_historic = include

    @property
    def include_historic(self) -> bool:
        return self._include_historic


# --------- Singleton --------- #
from localis.registries.macroregion_registry import macroregions

countries = CountryRegistry(macroregions=macroregions)
