from localis.models import CountryModel
from localis.registries import Registry
from localis.indexes import FilterIndex


class CountryRegistry(Registry[CountryModel]):
    REGISTRY_NAME = "countries"
    _MODEL_CLS = CountryModel

    def _parse_row(self, id: int, row: list[str]):
        if id == 0:
            return

        name, official_name, aliases, alpha2, alpha3, numeric, flag, search_tokens = row

        country = CountryModel(
            id=id,
            name=name,
            official_name=official_name,
            aliases=[alt for alt in aliases.split("|") if alt],
            alpha2=alpha2,
            alpha3=alpha3,
            numeric=numeric,
            flag=flag,
        )

        country.search_tokens = search_tokens
        self._cache[id] = country

    def lookup(self, identifier: str | int) -> CountryModel | None:
        """Get a country by its alpha2, alpha3, numeric code, or id."""
        return super().lookup(identifier)

    def load_filters(self):
        self._filter_index = FilterIndex(
            cache=self.cache, filter_fields=self._MODEL_CLS.FILTER_FIELDS
        )

    def filter(
        self, *, name: str = None, limit: int = None, **kwargs
    ) -> list[CountryModel]:
        """Filter countries by any of its names (name, official_name, or aliases)."""
        return super().filter(name=name, limit=limit, **kwargs)

    def search(self, query, limit=None) -> list[tuple[CountryModel, float]]:
        """Search countries by any of its names (name, official_name, or aliases)."""
        return super().search(query, limit)


countries = CountryRegistry()
