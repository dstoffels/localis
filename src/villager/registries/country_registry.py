from .registry import Registry
from ..db.models import CountryModel, db
from ..types import Country
from ..literals import CountryCode, CountryName, CountryNumeric
from typing import Optional
from ..utils import normalize
from collections import Counter


class CountryRegistry(Registry[CountryModel, Country]):
    """
    Registry for managing Country entities.

    Supports get by alpha2, alpha3 & numeric codes, lookup by country name with support for some aliases/former names,
    and fuzzy search.
    """

    def __init__(self, model_cls, dto_cls):
        super().__init__(model_cls, dto_cls)

    def get(self, identifier: CountryCode | CountryNumeric) -> Optional[Country]:
        if not identifier:
            return None

        identifier = normalize(identifier)

        if isinstance(identifier, int):
            model: CountryModel = self._model_cls.get_or_none(
                CountryModel.numeric == identifier
            )
        else:
            identifier = self.CODE_ALIASES.get(identifier.lower(), identifier)
            model: CountryModel = self._model_cls.get_or_none(
                (CountryModel.alpha2.collate("NOCASE") == identifier)
                | (CountryModel.alpha3.collate("NOCASE") == identifier)
            )

        if model:
            return model.to_dto()

    def lookup(self, identifier: CountryName) -> list[Country]:
        """Lookup a country by exact name."""
        if not identifier:
            return []

        identifier = self.ALIASES.get(identifier.lower(), identifier)
        identifier = normalize(identifier)

        models: list[CountryModel] = self._model_cls.select().where(
            CountryModel.normalized_name.collate("NOCASE") == identifier
        )
        return [m.to_dto() for m in models]

    def search(self, query, limit=5, **kwargs) -> list[tuple[Country, float]]:
        """Fuzzy search countries by name, alpha-2, or alpha-3 code.

        Returns a list of (Country, match_score) tuples."""
        if not query:
            return []

        # Lookup exact matches first
        if len(query) in [2, 3]:
            exact_match = self.get(query)
            if exact_match:
                return [(exact_match, 1.0)]

        exact_matches = self.lookup(query)
        if exact_matches:
            return [(m, 1.0) for m in exact_matches]

        return self._fuzzy_search(query, limit)

    def _build_sql(self):
        return """SELECT c.*, tokens FROM countries_fts f
        JOIN countries c ON f.rowid = c.id
        WHERE f.tokens MATCH ?
        LIMIT ?"""

    CODE_ALIASES = {
        "uk": "GB",
    }

    ALIASES = {
        "england": "United Kingdom",
        "scotland": "United Kingdom",
        "wales": "United Kingdom",
        "northern ireland": "United Kingdom",
        "great britain": "United Kingdom",
        "britain": "United Kingdom",
        "united states of america": "United States",
        "america": "United States",
        "czech republic": "Czechia",
        "ivory coast": "Côte d'Ivoire",
        "cote d'ivoire": "Côte d'Ivoire",
        "burma": "Myanmar",
        "swaziland": "Eswatini",
        "holland": "Netherlands",
        "macedonia": "North Macedonia",
        "cape verde": "Cabo Verde",
        "laos": "Lao People's Democratic Republic",
        "syria": "Syrian Arab Republic",
        "russia": "Russian Federation",
        "ussr": "Russian Federation",
        "soviet union": "Russian Federation",
        "vietnam": "Viet Nam",
        "zaire": "Congo",
        "brunei": "Brunei Darussalam",
        "são tomé and príncipe": "Sao Tome and Principe",
        "east timor": "Timor-Leste",
        "yugoslavia": "Serbia",
        "east germany": "Germany",
        "west germany": "Germany",
    }

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
