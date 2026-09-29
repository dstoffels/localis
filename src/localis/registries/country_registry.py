from localis.models import CountryModel, CountryView, Country
from localis.registries import Registry


class CountryRegistry(Registry[Country]):
    REGISTRY_NAME = "countries"
    _MODEL_CLS = CountryModel

    def build_cache(self) -> dict[int, CountryView]:
        return CountryView.load(self._data_filepath)

    def lookup(self, identifier: str | int) -> Country | None:
        """Get a country by its alpha2, alpha3, numeric code, or id."""
        return super().lookup(identifier)

    def filter(
        self, *, name: str | None = None, limit: int | None = None, **kwargs
    ) -> list[Country]:
        """Filter countries by any of its names (name, official_name, or aliases)."""
        return super().filter(name=name, limit=limit, **kwargs)

    def search(
        self, query: str, limit: int = 10, **kwargs
    ) -> list[tuple[Country, float]]:
        """Search countries by any of its names (name, official_name, or aliases)."""
        return super().search(query, limit, **kwargs)


# --------- Singleton --------- #
countries = CountryRegistry()
