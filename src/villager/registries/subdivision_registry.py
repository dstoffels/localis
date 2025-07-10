from .registry import Registry
from ..types import Subdivision
from typing import Callable, Optional
from ..db import SubdivisionModel, CountryModel
from ..literals import CountryCode, CountryName, CountryNumeric
from rapidfuzz import fuzz
from peewee import prefetch
from villager.utils import normalize


class SubdivisionRegistry(Registry[SubdivisionModel, Subdivision]):
    """
    Registry for managing Subdivision entities.

    Supports exact lookup by ISO code, alpha2, or country code,
    fuzzy search by these keys, and filtering by country or country code.
    """

    def __init__(self, model_cls, dto_cls):
        super().__init__(model_cls, dto_cls)

    def get(self, identifier: str) -> Subdivision:
        """Fetch a subdivision by exact iso code."""
        if not identifier:
            return None

        identifier = identifier.upper().strip()

        model: SubdivisionModel = self._model_cls.get_or_none(
            SubdivisionModel.iso_code == identifier
        )

        if model:
            return model.to_dto()

    def lookup(self, identifier):
        """Lookup a subdivision by exact name"""
        if not identifier:
            return []

        identifier = normalize(identifier)

        models: list[SubdivisionModel] = self._model_cls.select().where(
            SubdivisionModel.normalized_name.collate("NOCASE") == identifier
        )

        return [m.to_dto() for m in models]

    def search(
        self, query, limit=5, country: CountryCode | CountryName = None, **kwargs
    ):
        """Search for subdivisions by name."""

        if not query:
            return []

        # find exact matches
        exact_matches = self.lookup(query)
        if exact_matches:
            return [(m, 1.0) for m in exact_matches]

        return self._fuzzy_search(query, limit)

    def _build_sql(self):
        return """SELECT s.*, c.*, tokens FROM subdivisions_fts f
        JOIN subdivisions s ON f.rowid = s.id
        JOIN countries c ON s.country_id = c.id
        WHERE f.tokens MATCH ?
        ORDER BY rank
        LIMIT ?
        """

    def _load_cache(self):
        return super()._load_cache(CountryModel)

    # def __init__(self, data: list[Subdivision]):
    #     self._data = data
    #     self._lookup_map: dict[str, list[Subdivision]] = defaultdict(list)
    #     self._by_country: dict[CountryName, list[Subdivision]] = defaultdict(list)
    #     self._by_country_code: dict[CountryCode, list[Subdivision]] = defaultdict(list)
    #     self._trie: Trie[Subdivision] = Trie[Subdivision]()

    #     # Build lookup maps and trie
    #     for s in data:

    #         self._by_country[self._normalize(s.country)].append(s)
    #         self._by_country_code[self._normalize(s.country_code)].append(s)

    #         keys = {
    #             self._normalize(s.name),
    #             self._normalize(s.iso_code),
    #             self._normalize(s.alpha2),
    #             self._normalize(f"{s.name} {s.alpha2}"),
    #             self._normalize(f"{s.name} {s.country_code}"),
    #             self._normalize(f"{s.name} {s.country}"),
    #         }

    #         for key in keys:
    #             self._lookup_map[key].append(s)
    #             self._trie.insert(key, s)

    # def by_country(self, name: CountryName):
    #     """List all subdivisions belonging to a given country by name."""
    #     return [s for s in self._data if s.country.lower() == name.lower()]

    # def by_country_code(self, code: CountryCode):
    #     """List all subdivisions belonging to a given country by country code."""
    #     return [s for s in self._data if s.country_code.lower() == code.lower()]

    # def get_types(self, country_code: CountryCode) -> list[str]:
    #     """Get all subdivision types for a given country code."""
    #     return sorted(
    #         set(
    #             s.type
    #             for s in self._data
    #             if s.country_code.lower() == country_code.lower()
    #         )
    #     )

    # def get(self, identifier: str) -> list[Subdivision]:
    #     """Retrieve a list of Subdivisions by name, ISO code, alpha2."""

    #     identifier = self._normalize(identifier)
    #     if not identifier:
    #         return []

    #     return self._lookup_map.get(identifier, [])

    # def get_by_country_name(
    #     self, identifier: str, country_name: CountryName
    # ) -> list[Subdivision]:
    #     """Retrieve country-name-filtered list of Subdivisions by name, ISO code, or alpha2."""
    #     identifier = self._normalize(identifier)
    #     country_subs = self.by_country(country_name)
    #     return [
    #         s
    #         for s in country_subs
    #         if identifier
    #         in {
    #             self._normalize(s.name),
    #             self._normalize(s.iso_code),
    #             self._normalize(s.alpha2),
    #         }
    #     ]

    # def get_by_country_code(
    #     self, identifier: str, country_code: CountryCode
    # ) -> list[Subdivision]:
    #     """Retrieve country-code-filtered list of Subdivisions by name, ISO code, or alpha2."""
    #     identifier = self._normalize(identifier)
    #     country_subs = self.by_country_code(country_code)
    #     return [
    #         s
    #         for s in country_subs
    #         if identifier
    #         in {
    #             self._normalize(s.name),
    #             self._normalize(s.iso_code),
    #             self._normalize(s.alpha2),
    #         }
    #     ]

    # def __search(
    #     self,
    #     query: str,
    #     limit: int,
    #     predicate: Optional[Callable[[Subdivision], bool]] = None,
    # ) -> list[tuple[Subdivision, float]]:
    #     query = self._normalize(query)
    #     if not query:
    #         return []

    #     # Get candidates filtered by predicate if given
    #     candidates = (
    #         self._trie.search_prefix(query, predicate=predicate)
    #         if predicate
    #         else self._trie.search_prefix(query)
    #     )
    #     if not candidates:
    #         return []

    #     # Dedupe candidates by identity
    #     unique_candidates = list({id(c): c for c in candidates}.values())

    #     # Compute best fuzzy score across name, iso_code, alpha2
    #     scored = []
    #     for candidate in unique_candidates:
    #         scores = [
    #             fuzz.ratio(query, self._normalize(candidate.name)),
    #             fuzz.ratio(query, self._normalize(candidate.iso_code)),
    #             fuzz.ratio(query, self._normalize(candidate.alpha2)),
    #         ]
    #         best_score = max(scores)
    #         scored.append((candidate, best_score))

    #     scored.sort(key=lambda x: x[1], reverse=True)
    #     return scored[:limit]

    # def search(self, query: str, limit: int = 5) -> list[tuple[Subdivision, float]]:
    #     """Perform a fuzzy search for subdivisions matching the query against name, ISO code, and alpha2 code. Returns a list of tuples containing the matched subdivision and a score indicating the similarity."""
    #     return self.__search(query, limit)

    # def search_by_country(
    #     self, query: str, country: CountryName | CountryCode, limit: int = 5
    # ) -> list[tuple[Subdivision, float]]:
    #     """Perform a fuzzy search for subdivisions matching the query against name, ISO code, and alpha2 code, filtered by country name or code."""
    #     country_key = self._normalize(country)

    #     def predicate(s: Subdivision):
    #         if len(country_key) == 2:
    #             return s.country_code.lower() == country_key
    #         return s.country.lower() == country_key

    #     return self.__search(query, limit, predicate)
