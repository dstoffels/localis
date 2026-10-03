from functools import cached_property
from typing import Iterator, Generic, Mapping, TypeVar
from pathlib import Path
from abc import ABC
from localis.entities import Entity
from localis.views import View
from localis.stores import Store
from localis.indexes import FilterIndex, SearchIndex, LookupIndex

T = TypeVar("T", bound=Entity)


class Registry(Generic[T], ABC):
    """Base API surface (get/lookup/iteration) backed by a lazily-cached View dict and its lookup index."""

    REGISTRY_NAME: str = ""

    def __init__(self, **kwargs):
        self._allowed_ids: set[int] | None = None

    @staticmethod
    def _is_id_allowed(id: int, allowed_ids: set[int]) -> bool:
        return id in allowed_ids

    @property
    def _data_path(self) -> Path:
        return Path(__file__).parent.parent / "data" / self.REGISTRY_NAME

    @property
    def _data_filepath(self) -> Path:
        return self._data_path / f"{self.REGISTRY_NAME}.tsv"

    @property
    def _lookup_filepath(self) -> Path:
        return self._data_path / "lookup_index_str.tsv"

    @property
    def _lookup_int_filepath(self) -> Path:
        return self._data_path / "lookup_index_int.tsv"

    @property
    def count(self) -> int:
        return self.__len__()

    @cached_property
    def _cache(self) -> Mapping[int, View[T, Store]]:
        if not self._data_filepath.exists():
            raise FileNotFoundError(f"Data file not found: {self._data_filepath}")

        return self.build_cache()

    def build_cache(self) -> Mapping[int, View[T, Store]]:
        """Build the id -> view mapping for this registry. Overridden per registry to
        supply whatever cross-referenced caches its view class needs."""
        raise NotImplementedError

    @cached_property
    def _lookup_index(self) -> LookupIndex:
        _ = self._cache
        return LookupIndex(
            filepath=self._lookup_filepath,
            int_filepath=self._lookup_int_filepath,
            predicate=self._is_id_allowed if self._allowed_ids is not None else None,
            allowed_ids=self._allowed_ids,
        )

    _CACHED_ATTRS: tuple[str, ...] = ("_cache", "_lookup_index")

    def invalidate_cache(self):
        for attr in self._CACHED_ATTRS:
            try:
                delattr(self, attr)
            except AttributeError:
                pass

    def force_cache(self):
        """Force-cache all data and indexes that have not yet been loaded."""
        for attr in self._CACHED_ATTRS:
            getattr(self, attr)

    def __iter__(self) -> Iterator[T]:
        for view in self._cache.values():
            yield view.to_entity()

    def __len__(self) -> int:
        return len(self._cache)

    # ----------- API METHODS ----------- #

    def get(self, id: int) -> T | None:
        """Get by localis ID."""
        model = self._cache.get(id)
        return model.to_entity() if model else None

    def lookup(self, identifier: str | int) -> T | None:
        """Fetches a single item by one of its other unique identifiers (use .get() for localis ID)."""
        model_id = self._lookup_index.get(identifier)
        model = self._cache.get(model_id) if model_id is not None else None
        return model.to_entity() if model else None


class QueryableRegistry(Registry[T]):
    """Full API surface: LookupRegistry plus filter/search over the filter and search indexes."""

    _CACHED_ATTRS = Registry._CACHED_ATTRS + ("_filter_index", "_search_index")

    @property
    def _filter_filepath(self) -> Path:
        return self._data_path / "filter_index.tsv"

    @property
    def _search_index_filepath(self) -> Path:
        return self._data_path / "search_index.bin.gz"

    @property
    def _search_index_offsets_filepath(self) -> Path:
        return self._data_path / "search_index_offsets.tsv"

    @property
    def _search_fields_filepath(self) -> Path:
        return self._data_path / "search_fields.tsv"

    @cached_property
    def _filter_index(self) -> FilterIndex:
        _ = self._cache
        return FilterIndex(
            filepath=self._filter_filepath,
            predicate=self._is_id_allowed if self._allowed_ids is not None else None,
            allowed_ids=self._allowed_ids,
        )

    @cached_property
    def _search_index(self) -> SearchIndex[T]:
        return SearchIndex(
            cache=self._cache,
            filepath=self._search_index_filepath,
            offsets_filepath=self._search_index_offsets_filepath,
            fields_filepath=self._search_fields_filepath,
            predicate=self._is_id_allowed if self._allowed_ids is not None else None,
            allowed_ids=self._allowed_ids,
        )

    # ----------- API METHODS ----------- #

    def filter(
        self, *, name: str | None = None, limit: int | None = None, **kwargs
    ) -> list[T]:
        """Filter by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive. Raises TypeError for a kwarg the registry can't filter by."""
        kwargs["name"] = name

        unknown = [k for k in kwargs if k not in self._filter_index.index]
        if unknown:
            raise TypeError(f"{type(self).__name__}.filter() got an unexpected keyword argument '{unknown[0]}'")

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
        return [r.to_entity() for r in results_list]

    def search(self, query: str, limit: int = 10, **kwargs) -> list[tuple[T, float]]:
        results = self._search_index.search(query=query, limit=limit)
        return [(r.to_entity(), score) for r, score in results]
