from typing import Iterator, Generic, TypeVar
from localis.models import Model
from abc import ABC
from localis.models import DTO
from pathlib import Path
import csv
from localis.indexes import FilterIndex, SearchIndex, LookupIndex
from localis.utils import ModelData

T = TypeVar("DTO", bound=DTO)


class Registry(Generic[T], ABC):
    """"""

    REGISTRY_NAME: str = ""
    _MODEL_CLS: type[Model]

    def __init__(self, **kwargs):
        # ---------- Lazy loaded attributes ---------- #
        self._cache: dict[int, ModelData] | None = None
        self._lookup_index: LookupIndex | None = None
        self._filter_index: FilterIndex | None = None
        self._search_index: SearchIndex | None = None

    @property
    def _data_path(self) -> Path:
        return Path(__file__).parent.parent / "data" / self.REGISTRY_NAME

    @property
    def _data_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}.tsv"

    @property
    def _lookup_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}_lookup_index.tsv"

    @property
    def _filter_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}_filter_index.tsv"

    @property
    def _search_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}_search_index.tsv"

    @property
    def count(self) -> int:
        return len(self.cache)

    # ----------- LAZY LOADERS ----------- #
    @property
    def cache(self) -> dict[int, ModelData]:
        if self._cache is None:
            # Load data file
            if not self._data_filepath.exists():
                raise FileNotFoundError(f"Data file not found: {self._data_filepath}")

            self._cache = {}
            try:
                with open(self._data_filepath, "r", encoding="utf-8") as f:
                    for id, line in enumerate(f, start=1):
                        row = line.split("\t")
                        self._cache[id] = self.parse_row(id, row)
            except Exception as e:
                raise e
        return self._cache

    def parse_row(self, id, row: list[str | int | None]) -> T:
        return self._MODEL_CLS.from_row(id, row)

    @property
    def lookup_index(self) -> LookupIndex:
        if self._lookup_index is None:
            self._lookup_index = LookupIndex(
                model_cls=self._MODEL_CLS,
                cache=self.cache,
                filepath=self._lookup_filepath,
            )
        return self._lookup_index

    @property
    def filter_index(self) -> FilterIndex:
        if self._filter_index is None:
            self._filter_index = FilterIndex(
                model_cls=self._MODEL_CLS,
                cache=self.cache,
                filepath=self._filter_filepath,
            )
        return self._filter_index

    @property
    def search_index(self) -> SearchIndex:
        if self._search_index is None:
            self._search_index = SearchIndex(
                model_cls=self._MODEL_CLS,
                cache=self.cache,
                filepath=self._search_filepath,
            )
        return self._search_index

    def __iter__(self) -> Iterator[T]:
        return iter([self._resolve_model(id) for id in self.cache.keys()])

    def __len__(self) -> int:
        return len(self.cache)

    # ----------- API METHODS ----------- #

    def get(self, id: int) -> T | None:
        """Get by localis ID."""
        return self.cache.get(id).dto

    def lookup(self, identifier: str | int) -> T | None:
        """Fetches a single item by one of its other unique identifiers (use .get() for localis ID)."""

        model_id = self.lookup_index.get(identifier)
        return self._resolve_model(model_id)

    def filter(self, *, name: str = None, limit: int = None, **kwargs) -> list[T]:
        """Filter by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs["name"] = name

        filter_kws = {k: v for k, v in kwargs.items() if v is not None}

        results: set[int] = None

        # short circuit
        if not filter_kws:
            return []

        for key, value in filter_kws.items():
            matches = self.filter_index.filter(filter_kw=key, field_value=value)

            # short circuit if any field fails to match, all or nothing
            if not matches:
                return []

            if results is None:
                results = matches
            else:
                results &= matches
        results_list = [self._resolve_model(id) for id in list(results)[:limit]]
        results_list.sort(key=lambda r: r.name)  # sort alphabetically by name
        return results_list

    def search(self, query: str, limit: int = None, **kwargs) -> list[tuple[T, float]]:
        return self.search_index.search(query=query, limit=limit)
