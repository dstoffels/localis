from typing import Iterable, Iterator, Union, Optional
from .types import Country, Subdivision
from difflib import get_close_matches
from typing import Generic, TypeVar
from .literals import CountryCode, CountryName, CountryNumeric
from rapidfuzz import process, fuzz
from abc import abstractmethod, ABC

T = TypeVar("T")


class Registry(Generic[T], ABC):
    def __init__(self, data: list[T]):
        self._data = data
        self._search_lookup: dict[str, T] = {}
        self._search_candidates: list[str] = []

    def __iter__(self) -> Iterator[T]:
        return iter(self._data)

    def __getitem__(self, index: int) -> T:
        return self._data[index]

    def __len__(self) -> int:
        return len(self._data)

    @property
    def count(self) -> int:
        return len(self._data)

    @abstractmethod
    def get(self, identifier: str) -> Optional[T]:
        pass

    def _search(
        self, query: str, lookup: dict[str, T], candidates: list[str], limit: int = 5
    ) -> list[tuple[T, float]]:
        query = query.strip().lower()
        if not query:
            return []

        matches = process.extract(query, candidates, scorer=fuzz.ratio, limit=limit * 3)

        seen = set()
        results = []
        for match_str, score, _ in matches:
            country = lookup.get(match_str)
            if country in seen:
                continue
            seen.add(country)
            if country:
                results.append((country, score))
            if len(results) >= limit:
                break
        return results

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[tuple[T, float]]:
        pass


class CountryRegistry(Registry[Country]):
    """
    Registry for managing Country entities.

    Supports exact lookup by alpha2, alpha3, numeric codes, or country name,
    as well as fuzzy search by these fields.
    """

    ALIASES = {
        "uk": "gb",
    }

    def __init__(self, data: list[Country]):
        self._data = data
        self._by_alpha2 = {c.alpha2.lower(): c for c in data}
        self._by_alpha3 = {c.alpha3.lower(): c for c in data}
        self._by_numeric = {c.numeric: c for c in data}
        self._by_name = {c.name.lower(): c for c in data}
        self._search_lookup = {**self._by_name, **self._by_alpha2, **self._by_alpha3}
        self._search_candidates = list(self._search_lookup.keys())
        self._init_aliases()

    def _init_aliases(self) -> None:
        for alias, a2 in self.ALIASES.items():
            country = self._by_alpha2.get(a2)
            if country:
                self._by_alpha2[alias] = country

    def get(
        self, identifier: CountryName | CountryCode | CountryNumeric
    ) -> Optional[Country]:
        """Retrieve a Country by its alpha2, alpha3, numeric code, or name."""
        try:
            num_id = int(identifier)
        except ValueError:
            num_id = None
            identifier = identifier.strip().lower()

        return (
            self._by_alpha2.get(identifier)
            or self._by_alpha3.get(identifier)
            or self._by_numeric.get(num_id)
            or self._by_name.get(identifier)
        )

    def search(self, query: str, limit: int = 5) -> list[tuple[Country, float]]:
        """Perform a fuzzy search for countries matching the query string to name, alpha2 code, or alpha3 code. Returns a list of tuples containing the matched country and a score indicating the similarity."""

        return self._search(query, self._search_lookup, self._search_candidates, limit)


class SubdivisionRegistry(Registry[Subdivision]):
    """
    Registry for managing Subdivision entities.

    Supports exact lookup by ISO code, alpha2, or country code,
    fuzzy search by these keys, and filtering by country or country code.
    """

    def __init__(self, data: list[Subdivision]):
        self._data = data
        self._by_name = {s.name.lower(): s for s in data}
        self._by_iso_code = {s.iso_code.lower(): s for s in data}
        self._by_alpha2 = {s.alpha2.lower(): s for s in data}
        self._by_country_code = {s.country_code.lower(): s for s in data}
        self._by_country = {s.country_name.lower(): s for s in data}
        self._search_lookup = {
            **self._by_name,
            **self._by_iso_code,
            **self._by_alpha2,
        }
        self._search_candidates = list(self._search_lookup.keys())

    def get(self, identifier: str) -> Optional[Subdivision]:
        """Retrieve a Subdivision by name, ISO code, or alpha2 code."""

        identifier = identifier.strip().lower()
        return (
            self._by_name.get(identifier)
            or self._by_iso_code.get(identifier)
            or self._by_alpha2.get(identifier)
        )

    def search(self, query, limit=5):
        """Perform a fuzzy search for subdivisions matching the query against name, ISO code, and alpha2 code. Returns a list of tuples containing the matched subdivision and a score indicating the similarity."""
        return self._search(query, self._search_lookup, self._search_candidates, limit)

    def by_country(self, name: CountryName):
        """List all subdivisions belonging to a given country by name."""
        return [s for s in self._data if s.country_name.lower() == name.lower()]

    def by_country_code(self, country_code: CountryCode):
        """List all subdivisions belonging to a given country by country code."""
        return [s for s in self._data if s.country_code.lower() == country_code.lower()]

    def get_types(self, country_code: CountryCode) -> list[str]:
        """Get all subdivision types for a given country code."""
        return sorted(
            set(
                s.type
                for s in self._data
                if s.country_code.lower() == country_code.lower()
            )
        )
