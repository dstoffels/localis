from functools import cached_property
import threading
from typing import Any, Iterator, Generic, Mapping, Self, TypeVar, overload
from pathlib import Path
from abc import ABC, abstractmethod
from localis.entities import Entity
from localis.views import View
from localis.stores import Store
from localis.indexes import FilterIndex, SearchIndex, LookupIndex
from localis.utils.data import CacheFilterPredicate

T = TypeVar("T", bound=Entity)
R = TypeVar("R", covariant=True)


class locked_cached_property(cached_property[R]):
    """A cached_property built under its registry's lock, so threads that reach a cold registry together build it once; reads of a built value take no lock."""

    # the overloads keep cached_property's typing: the descriptor on the class, the built value on an instance
    @overload
    def __get__(self, instance: None, owner: type[Any] | None = None) -> Self: ...
    @overload
    def __get__(self, instance: object, owner: type[Any] | None = None) -> R: ...
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

    def __init__(self):
        # a load-time filter on the data file's rows, such as CityRegistry's population threshold; None loads every row
        self._row_filter: CacheFilterPredicate | None = None
        # reentrant, since building an index first builds the cache it reads
        self._lock = threading.RLock()

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

    @locked_cached_property
    def _cache(self) -> Mapping[int, View[T, Store]]:
        if not self._data_filepath.exists():
            raise FileNotFoundError(f"Data file not found: {self._data_filepath}")

        return self._build_cache()

    @abstractmethod
    def _build_cache(self) -> Mapping[int, View[T, Store]]:
        """The registry's id -> view mapping, built with whatever other registries' views its views reference."""

    @locked_cached_property
    def _allowed_ids(self) -> set[int] | None:
        """The ids the row filter kept, the only ones the indexes load; None when every row loaded."""
        return set(self._cache) if self._row_filter is not None else None

    @locked_cached_property
    def _lookup_index(self) -> LookupIndex:
        return LookupIndex(
            filepath=self._lookup_filepath,
            int_filepath=self._lookup_int_filepath,
            allowed_ids=self._allowed_ids,
        )

    _CACHED_ATTRS: tuple[str, ...] = ("_cache", "_allowed_ids", "_lookup_index")

    def _invalidate_cache(self):
        with self._lock:
            for attr in self._CACHED_ATTRS:
                vars(self).pop(attr, None)

    def force_cache(self):
        """Force-cache all data and indexes that have not yet been loaded."""
        for attr in self._CACHED_ATTRS:
            getattr(self, attr)

    def _hidden_ids(self) -> frozenset[int]:
        """The ids that iteration, filter() and search() skip, which get() and lookup() still resolve; none by default."""
        return frozenset()

    def __iter__(self) -> Iterator[T]:
        hidden = self._hidden_ids()
        for id, view in self._cache.items():
            if id not in hidden:
                yield view.to_entity()

    def __len__(self) -> int:
        """How many records iteration yields, leaving out hidden ones."""
        return len(self._cache) - len(self._hidden_ids())

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
    """Registry plus filter() and search() over the filter and search indexes."""

    _CACHED_ATTRS = Registry._CACHED_ATTRS + ("_filter_index", "_search_index")

    NAME_FIELDS: tuple[str, ...] = ()
    """View fields holding the record's names, fuzzy-matched against a search query; context is matched through the context trigram index. Can be nested fields using dot notation."""

    @property
    def _filter_prefix(self) -> Path:
        return self._data_path / "filter_index"

    @locked_cached_property
    def _filter_index(self) -> FilterIndex:
        return FilterIndex(
            prefix=self._filter_prefix,
            allowed_ids=self._allowed_ids,
        )

    @locked_cached_property
    def _search_index(self) -> SearchIndex[T]:
        return SearchIndex(
            cache=self._cache,
            data_path=self._data_path,
            name_fields=self.NAME_FIELDS,
            allowed_ids=self._allowed_ids,
        )

    # ----------- API METHODS ----------- #

    @staticmethod
    def _check_limit(limit: int | None) -> None:
        # a slice would read a negative limit as "all but the last few"
        if limit is not None and (not isinstance(limit, int) or isinstance(limit, bool) or limit < 1):
            raise ValueError(f"limit must be a positive integer, got {limit!r}")

    def filter(self, *, name: str | None = None, limit: int | None = None) -> list[T]:
        """Filter by name; each registry adds its own fields. Exact, case-insensitive matches, combined with AND, sorted by name; a field given MISSING matches the records with no value in it. Raises TypeError when no field is given, and ValueError for a limit below 1."""
        return self._filter(limit, name=name)

    def _filter(self, limit: int | None, **fields) -> list[T]:
        """filter() over the given fields, None ones ignored."""
        self._check_limit(limit)
        filter_kws = {k: v for k, v in fields.items() if v is not None}
        if not filter_kws:
            raise TypeError(f"{type(self).__name__}.filter() needs at least one field")

        # each registry's filter() signature names its fields, so this only catches a signature out of step with the shipped index
        unknown = [k for k in fields if k not in self._filter_index.index]
        if unknown:
            raise TypeError(f"{type(self).__name__}.filter() got an unexpected keyword argument '{unknown[0]}'")

        results: set[int] | None = None

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
        results -= self._hidden_ids()

        results_list = [self._cache[id] for id in results]
        results_list.sort(key=lambda r: r.name)  # sort alphabetically by name
        if limit is not None:
            results_list = results_list[:limit]
        return [r.to_entity() for r in results_list]

    def search(self, query: str, limit: int = 10) -> list[tuple[T, float]]:
        """Typo-tolerant search: up to `limit` (entity, score) pairs, best first. Raises ValueError for a limit below 1."""
        self._check_limit(limit)
        results = self._search_index.search(query=query, limit=limit, exclude=self._hidden_ids())
        return [(r.to_entity(), score) for r, score in results]
