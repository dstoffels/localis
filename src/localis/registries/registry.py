from functools import cached_property
from typing import Iterator, Generic, TypeVar
from pathlib import Path
from abc import ABC
from localis.models import Model, DTO
from localis.indexes import FilterIndex, SearchIndex, LookupIndex

T = TypeVar("T", bound=DTO)


class Registry(Generic[T], ABC):
    """"""

    REGISTRY_NAME: str = ""
    LAZY_LOAD = False
    _MODEL_CLS: type[Model]

    def __init__(self, **kwargs):
        if not self.LAZY_LOAD:
            _ = self._cache

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
        return self.__len__()

    @cached_property
    def _cache(self) -> dict[int, Model]:
        if not self._data_filepath.exists():
            raise FileNotFoundError(f"Data file not found: {self._data_filepath}")

        cache: dict[int, Model] = {}
        with open(self._data_filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.strip().split("\t")
                cache[id] = self.parse_row(id, row, cache)
        return cache

    @cached_property
    def _lookup_index(self) -> LookupIndex:
        return LookupIndex(
            model_cls=self._MODEL_CLS,
            cache=self._cache,
            filepath=self._lookup_filepath,
        )

    @cached_property
    def _filter_index(self) -> FilterIndex:
        return FilterIndex(
            model_cls=self._MODEL_CLS,
            cache=self._cache,
            filepath=self._filter_filepath,
        )

    @cached_property
    def _search_index(self) -> SearchIndex:
        return SearchIndex(
            model_cls=self._MODEL_CLS,
            cache=self._cache,
            filepath=self._search_filepath,
        )

    def parse_row(self, id, row: list[str], cache: dict[int, Model]) -> Model:
        return self._MODEL_CLS.from_row(id, row)

    def force_cache(self):
        """Force-cache all data and indexes that have not yet been loaded."""
        _ = self._cache
        _ = self._lookup_index
        _ = self._filter_index
        _ = self._search_index

    def __iter__(self) -> Iterator[T]:
        return iter([m.to_dto() for m in self._cache.values()])

    def __len__(self) -> int:
        return len(self._cache)

    # ----------- API METHODS ----------- #

    def get(self, id: int) -> T | None:
        """Get by localis ID."""
        model = self._cache.get(id)
        return model.to_dto() if model else None

    def lookup(self, identifier: str | int) -> T | None:
        """Fetches a single item by one of its other unique identifiers (use .get() for localis ID)."""
        model_id = self._lookup_index.get(identifier)
        model = self._cache.get(model_id) if model_id is not None else None
        return model.to_dto() if model else None

    def filter(
        self, *, name: str | None = None, limit: int | None = None, **kwargs
    ) -> list[T]:
        """Filter by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs["name"] = name

        filter_kws = {k: v for k, v in kwargs.items() if v is not None}

        results: set[int] | None = None

        # short circuit
        if not filter_kws:
            return []

        for key, value in filter_kws.items():
            matches = self._filter_index.get(filter_kw=key, field_value=value)

            # short circuit if any field fails to match, all or nothing
            if not matches:
                return []

            if results is None:
                results = matches
            else:
                results &= matches

        assert results is not None, "Filter results should not be None at this point."

        results_list = [self._cache[id] for id in results]
        results_list.sort(key=lambda r: r.name)  # sort alphabetically by name
        if limit is not None:
            results_list = results_list[:limit]
        return [r.to_dto() for r in results_list]

    def search(self, query: str, limit: int = 10, **kwargs) -> list[tuple[T, float]]:
        results = self._search_index.search(query=query, limit=limit)
        return [(r.to_dto(), score) for r, score in results]
