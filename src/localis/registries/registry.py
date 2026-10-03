from functools import cached_property
import threading
from typing import Iterator, Generic, Mapping, TypeVar
from pathlib import Path
from abc import ABC
from localis.entities import Entity
from localis.views import View
from localis.stores import Store
from localis.indexes import FilterIndex, SearchIndex, LookupIndex

T = TypeVar("T", bound=Entity)


class locked_cached_property(cached_property):
    """A cached_property built under its registry's lock, so threads that reach a cold registry together build it once; reads of a built value take no lock."""

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        cache = instance.__dict__
        if self.attrname in cache:
            return cache[self.attrname]
        with instance._lock:
            # another thread may have built it while this one waited
            if self.attrname not in cache:
                cache[self.attrname] = self.func(instance)
            return cache[self.attrname]


class Registry(Generic[T], ABC):
    """Base API surface (get/lookup/iteration) backed by a lazily-cached View dict and its lookup index."""

    REGISTRY_NAME: str = ""

    def __init__(self, **kwargs):
        self._allowed_ids: set[int] | None = None
        # reentrant, since building an index first builds the cache it reads
        self._lock = threading.RLock()

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

    @locked_cached_property
    def _cache(self) -> Mapping[int, View[T, Store]]:
        if not self._data_filepath.exists():
            raise FileNotFoundError(f"Data file not found: {self._data_filepath}")

        return self.build_cache()

    def build_cache(self) -> Mapping[int, View[T, Store]]:
        """Build the id -> view mapping for this registry. Overridden per registry to
        supply whatever cross-referenced caches its view class needs."""
        raise NotImplementedError

    @locked_cached_property
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
        with self._lock:
            for attr in self._CACHED_ATTRS:
                self.__dict__.pop(attr, None)

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

    NAME_FIELDS: tuple[str, ...] = ()
    """View fields holding the record's names, fuzzy-matched against a search query; context is matched through the context trigram index. Can be nested fields using dot notation."""

    @property
    def _filter_filepath(self) -> Path:
        return self._data_path / "filter_index.tsv"

    @locked_cached_property
    def _filter_index(self) -> FilterIndex:
        _ = self._cache
        return FilterIndex(
            filepath=self._filter_filepath,
            predicate=self._is_id_allowed if self._allowed_ids is not None else None,
            allowed_ids=self._allowed_ids,
        )

    @locked_cached_property
    def _search_index(self) -> SearchIndex[T]:
        return SearchIndex(
            cache=self._cache,
            filepath=self._data_path,
            name_fields=self.NAME_FIELDS,
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
