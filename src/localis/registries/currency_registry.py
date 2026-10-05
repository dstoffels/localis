from typing import Mapping
from localis.entities import Currency
from localis.views import CurrencyView
from localis.registries import QueryableRegistry


class CurrencyRegistry(QueryableRegistry[Currency]):
    REGISTRY_NAME = "currencies"
    NAME_FIELDS = ("name",)

    def _build_cache(self) -> Mapping[int, CurrencyView]:
        return CurrencyView.load(self._data_filepath)

    def lookup(self, identifier: str | int) -> Currency | None:
        """Get a currency by its ISO 4217 alpha3 or numeric code (an int); use .get() for the localis id."""
        return super().lookup(identifier)

    def filter(self, *, name: str | None = None, limit: int | None = None) -> list[Currency]:
        """Filter currencies by name."""
        return self._filter(limit, name=name)

    def search(self, query: str, limit: int = 10) -> list[tuple[Currency, float]]:
        """Search currencies by name."""
        return super().search(query, limit)


# --------- Singleton --------- #
currencies = CurrencyRegistry()
