from localis.models import CountryModel, Country
from localis.registries import Registry


class CountryRegistry(Registry[CountryModel]):
    REGISTRY_NAME = "countries"
    _MODEL_CLS = CountryModel

    def lookup(self, identifier: str | int) -> Country | None:
        """Get a country by its alpha2, alpha3, numeric code, or id."""
        return super().lookup(identifier)

    def filter(self, *, name: str = None, limit: int = None, **kwargs) -> list[Country]:
        """Filter countries by any of its names (name, official_name, or aliases)."""
        return super().filter(name=name, limit=limit, **kwargs)

    def search(self, query, limit=None) -> list[tuple[Country, float]]:
        """Search countries by any of its names (name, official_name, or aliases)."""
        return super().search(query, limit)


# --------- Singleton --------- #
countries = CountryRegistry()
