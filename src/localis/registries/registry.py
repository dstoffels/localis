from typing import Iterator, Generic, TypeVar
from localis.models import Model
from abc import ABC, abstractmethod
from pathlib import Path
import gzip
import pickle
from localis.indexes import FilterIndex, SearchEngine, LookupIndex

T = TypeVar("Model", bound=Model)


class Registry(Generic[T], ABC):
    """"""

    REGISTRY_NAME: str = ""

    @property
    def _DATA_PATH(self) -> Path:
        return Path(__file__).parent.parent / "data" / self.REGISTRY_NAME

    @property
    def DATAFILE_PATH(self) -> Path:
        return self._DATA_PATH / f"{self.REGISTRY_NAME}.pkl.gz"

    @property
    def LOOKUPFILE_PATH(self) -> Path:
        return self._DATA_PATH / f"{self.REGISTRY_NAME}_lookup_index.pkl.gz"

    @property
    def FILTERFILE_PATH(self) -> Path:
        return self._DATA_PATH / f"{self.REGISTRY_NAME}_filter_index.pkl.gz"

    @property
    def SEARCHFILE_PATH(self) -> Path:
        return self._DATA_PATH / f"{self.REGISTRY_NAME}_search_index.pkl.gz"

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
            if not self.DATAFILE_PATH.exists():
                raise FileNotFoundError(f"Data file not found: {self.DATAFILE_PATH}")

            try:
                with gzip.open(self.DATAFILE_PATH, "rb") as f:
                    self._cache = pickle.load(f)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to load data file: {self.DATAFILE_PATH}"
                ) from e
        return self._cache

    @property
    def lookup_index(self):
        if self._lookup_index is None:
            self.lookup_index = LookupIndex(
                model_cls=self.MODEL_CLS,
                cache=self.cache,
                filepath=self.LOOKUPFILE_PATH,
            )
        return self._lookup_index

    @property
    def filter_index(self):
        if self._filter_index is None:
            self.filter_index = FilterIndex(
                model_cls=self.MODEL_CLS,
                cache=self.cache,
                filepath=self.FILTERFILE_PATH,
            )
        return self._filter_index

    @property
    def search_index(self):
        if self._search_index is None:
            self.search_index = SearchEngine(
                model_cls=self.MODEL_CLS,
                cache=self.cache,
                filepath=self.SEARCHFILE_PATH,
            )
        return self._search_index

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
