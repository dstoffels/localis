from typing import Iterator, Generic, TypeVar
from localis.models import Model
from abc import ABC, abstractmethod
from pathlib import Path
import gzip
import json
from localis.indexes import FilterIndex, SearchEngine, LookupIndex

T = TypeVar("Model", bound=Model)


class Registry(Generic[T], ABC):
    """"""

    DATA_PATH = Path(__file__).parent.parent / "data"
    DATAFILE: str = ""
    MODEL_CLS: type[Model]

    def __init__(self, **kwargs):
        self._cache: dict[int, T] | None = None  # id-model map
        self._lookup_index: dict[str | int, dict] | None = None
        self._filter_index: FilterIndex | None = None
        self._search_index: SearchEngine | None = None

    @property
    def count(self) -> int:
        return len(self.cache)

    # ----------- LAZY LOADERS ----------- #
    @property
    def cache(self) -> dict[int, T]:
        if self._cache is None:
            self.load()
        return self._cache

    @property
    def lookup_index(self):
        if self._lookup_index is None:
            self.load_lookups()
        return self._lookup_index

    @property
    def filter_index(self):
        if self._filter_index is None:
            self.load_filters()
        return self._filter_index

    @property
    def search_index(self):
        if self._search_index is None:
            self.load_search_index()
        return self._search_index

    def load(self) -> None:
        filepath = self.DATA_PATH / self.DATAFILE
        if not filepath.exists():
            raise FileNotFoundError(f"Data file not found: {filepath}")

        try:
            bytes = gzip.open(filepath, "rb").read()
            self._cache = json.loads(bytes.decode("utf-8"))
        except Exception as e:
            raise RuntimeError(f"Failed to load data file: {filepath}") from e

    @abstractmethod
    def _parse_row(self, id: int, row: dict):
        raise NotImplementedError("_parse_row must be implemented in subclass")

    def __iter__(self) -> Iterator[T]:
        return iter(self.cache.values())

    def __getitem__(self, index: int) -> T:
        return list(self.cache.values())[index]

    def __len__(self) -> int:
        return len(self.cache)

    # ----------- API METHODS ----------- #

    # ----------- GET ----------- #
    # def load_lookups(self):
    #     self._lookup_index = LookupIndex(self.cache, self.MODEL_CLS.LOOKUP_FIELDS)

    def get(self, identifier: str | int) -> T:
        """Fetches a single item by one of its unique identifiers. Raises a ValueError if multiple kwargs are assigned."""

        return self.lookup_index.get(identifier)

    # ----------- FILTER ----------- #

    # def load_filters(self):
    #     self._filter_index = FilterIndex(self.cache, self.MODEL_CLS.FILTER_FIELDS)

    def filter(self, *, name: str = None, limit: int = None, **kwargs) -> list[T]:
        """Filter by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs["name"] = name

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        results: set[int] = None

        # short circuit
        if not kwargs:
            return []

        for key, value in kwargs.items():
            matches = self.filter_index.get(key, value)

            # short circuit if any field fails to match, all or nothing
            if not matches:
                return []

            if results is None:
                results = matches
            else:
                results &= matches
        results_list = [self.cache[id] for id in results]
        results_list.sort(key=lambda r: r.name)  # sort alphabetically by name
        return results_list[:limit]

    # ----------- SEARCH ----------- #
    # def load_search_index(self):
    #     self._search_index = SearchEngine(self.cache)

    def search(self, query: str, limit: int = None, **kwargs) -> list[tuple[T, float]]:
        return self.search_index.search(query=query, limit=limit)
