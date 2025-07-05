from .registry import Registry
from ..db.models import CountryModel
from ..types import Country
from ..literals import CountryCode, CountryName, CountryNumeric
from typing import Optional
from rapidfuzz import process, fuzz
from peewee import fn


class CountryRegistry(Registry[CountryModel, Country]):
    """
    Registry for managing Country entities.

    Supports exact lookup by alpha2, alpha3, numeric codes, or country name,
    as well as fuzzy search by these fields.
    """

    ALIASES = {
        "uk": "gb",
    }

    def __init__(self, db, model):
        super().__init__(db, model)

    def get(self, identifier: CountryCode | CountryNumeric) -> Optional[Country]:
        if not identifier:
            return None

        if isinstance(identifier, int):
            model = self._model.get_or_none(CountryModel.numeric == identifier)
        else:
            model = self._model.get_or_none(
                (fn.LOWER(CountryModel.alpha2.collate("NOCASE")) == identifier.lower())
                | (
                    fn.LOWER(CountryModel.alpha3.collate("NOCASE"))
                    == identifier.lower()
                )
            )
        if model:
            return model.to_dto()

    def lookup(self, identifier: CountryName) -> list[Country]:
        """Lookup a country by exact name."""
        if not identifier:
            return []

        models: list[CountryModel] = self._model.select().where(
            fn.LOWER(CountryModel.name.collate("NOCASE")) == identifier.lower()
        )
        if models:
            return [m.to_dto() for m in models]
        return []

    def search(self, query, limit=5):
        return super().search(query, limit)

    def _load_cache(self) -> list[Country]:
        return super()._load_cache()

        # lookup caches

    #     self._by_name: dict[str, Country] = {}
    #     self._by_code: dict[str, Country] = {}
    #     self._by_numeric: dict[str, Country] = {}

    #     for c in self._cache:
    #         name = self._normalize(c.name)
    #         self._by_name[name] = c

    #         self._by_code[c.alpha2.lower()] = c
    #         self._by_code[c.alpha3.lower()] = c

    #         self._by_numeric[c.numeric] = c

    #     # aliases
    #     for alias, a2 in self.ALIASES.items():
    #         country = self._by_code.get(a2)
    #         if country:
    #             self._by_code[alias] = country

    # def get(
    #     self, identifier: CountryName | CountryCode | CountryNumeric
    # ) -> Optional[Country]:
    #     if isinstance(identifier, int):
    #         return self._by_numeric.get(identifier)

    #     if len(identifier) in [2, 3]:
    #         return self._by_code.get(identifier.lower())

    #     identifier = self._normalize(identifier)
    #     return self._by_name.get(identifier)

    # def search(self, query: str | int, limit=5) -> list[tuple[Country, float]]:
    #     query = self._normalize(query)
    #     if not query:
    #         return []

    #     choices = {
    #         **self._by_name,
    #         **self._by_code,
    #     }

    #     seen = {}
    #     for match, score, _ in process.extract(
    #         query, choices.keys(), scorer=fuzz.ratio, limit=limit
    #     ):
    #         country = choices[match]
    #         if country.alpha2 in seen:
    #             if score > seen[country.alpha2][1]:
    #                 seen[country.alpha2] = (country, score)
    #         else:
    #             seen[country.alpha2] = (country, score)

    #     return sorted(seen.values(), key=lambda x: x[1], reverse=True)[:limit]

    # def _search(

    #     self, query: str, lookups: list[dict[str, T]], limit: int = 5
    # ) -> list[tuple[T, float]]:
    #     query = query.strip().lower()
    #     if not query:
    #         return []

    #     scorer = self._get_scorer(query)

    #     scored: dict[T, float] = {}

    #     for lookup in lookups:
    #         matches = process.extract(
    #             query,
    #             list(lookup.keys()),
    #             scorer=scorer,
    #             limit=limit * 3,
    #         )
    #         for match_str, score, _ in matches:
    #             item = lookup[match_str]
    #             if item not in scored or score > scored[item]:
    #                 scored[item] = score

    #     return sorted(scored.items(), key=lambda x: x[1], reverse=True)[:limit]

    # def __init__(self, data: list[Country]):
    #     self._data = data
    #     self._by_alpha2 = {c.alpha2.lower(): c for c in data}
    #     self._by_alpha3 = {c.alpha3.lower(): c for c in data}
    #     self._by_numeric = {c.numeric: c for c in data}
    #     self._by_name = {c.name.lower(): c for c in data}
    #     self._init_aliases()

    # def _init_aliases(self) -> None:
    #     for alias, a2 in self.ALIASES.items():
    #         country = self._by_alpha2.get(a2)
    #         if country:
    #             self._by_alpha2[alias] = country

    # def get(
    #     self, identifier: CountryName | CountryCode | CountryNumeric
    # ) -> Optional[Country]:
    #     """Retrieve a Country by its alpha2, alpha3, numeric code, or name."""
    #     try:
    #         num_id = int(identifier)
    #     except ValueError:
    #         num_id = None
    #         identifier = identifier.strip().lower()

    #     return (
    #         self._by_alpha2.get(identifier)
    #         or self._by_alpha3.get(identifier)
    #         or self._by_numeric.get(num_id)
    #         or self._by_name.get(identifier)
    #     )

    # def search(self, query: str, limit: int = 5) -> list[tuple[Country, float]]:
    #     """Perform a fuzzy search for countries matching the query string to name, alpha2 code, or alpha3 code. Returns a list of tuples containing the matched country and a score indicating the similarity."""

    #     lookups = [
    #         self._by_alpha2,
    #         self._by_alpha3,
    #         self._by_name,
    #     ]

    #     return self._search(query, lookups=lookups, limit=limit)
