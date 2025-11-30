from typing import Iterator, Generic, TypeVar
from localis.data import Model
from abc import ABC, abstractmethod
from pathlib import Path
import csv
from localis.index import Index, FilterIndex, SearchEngine
from functools import wraps


def is_loaded(cache_attr: str = "_cache", callback_attr: str = "load"):
    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            cache = getattr(self, cache_attr)
            if cache == None:
                callback = getattr(self, callback_attr)
                callback()

            return func(self, *args, **kwargs)

        return wrapper

    return decorator


T = TypeVar("Model", bound=Model)


class Registry(Generic[T], ABC):
    """"""

    DATA_PATH = Path(__file__).parent.parent / "data" / "fixtures"
    DATAFILE: str = ""
    MODEL_CLS: type[Model] = None

    def __init__(self, **kwargs):
        self._cache: dict[int, T] = None  # id-model map
        self._lookup_index: dict[str | int, dict] = None
        self._filter_index: FilterIndex = None
        self._search_index: SearchEngine = None

    @property
    def count(self) -> int:
        return len(self.cache)

    @property
    def cache(self):
        if self._cache is None:
            self.load()
        return self._cache

    def load(self) -> None:
        self._cache = {}
        with open(self.DATA_PATH / self.DATAFILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            next(reader)

            for id, row in enumerate(reader, 1):
                self._parse_row(id, row)

    @abstractmethod
    def _parse_row(self, id: int, row: dict):
        pass

    def __iter__(self) -> Iterator[T]:
        return iter(self.cache.values())

    def __getitem__(self, index: int) -> T:
        return list(self.cache.values())[index]

    def __len__(self) -> int:
        return len(self.cache)

    def load_lookups(self):
        self._lookup_index = {}

    @is_loaded("_lookup_index", "load_lookups")
    def get(self, *, id: int = None, **kwargs) -> T:
        """Fetches a single item by one of its unique identifiers. Raises a ValueError if multiple kwargs are assigned."""
        if id is not None and len([v for v in kwargs.values() if v is not None]) > 0:
            raise ValueError("get can only accept one keyword argument at a time.")

        if id is not None:
            return self.cache.get(id)  # returns None if id not found

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        for v in kwargs.values():
            return self._lookup_index.get(v)

    def load_filters(self):
        self._filter_index = Index[T]()

    @is_loaded("_filter_index", "load_filters")
    def filter(self, *, name: str = None, **kwargs) -> list[T]:
        """Filter by exact matches on specified fields with AND logic when filtering by multiple fields. Case insensitive."""
        kwargs["name"] = name

        kwargs = {k: v for k, v in kwargs.items() if v is not None}

        results: set[int] = None

        # short circuit
        if not kwargs:
            return []

        for key, value in kwargs.items():
            matches = self._filter_index.get(key, value)

            # short circuit if any field fails to match, all or nothing
            if not matches:
                return []

            if results is None:
                results = matches
            else:
                results &= matches
        results_list = [self.cache[id] for id in results]
        results_list.sort(key=lambda r: r.name)  # sort alphabetically by name
        return results_list

    def load_searches(self):
        self._search_index = SearchEngine(self.cache)

    @is_loaded("_search_index", "load_searches")
    def search(self, query: str, limit: int = None):
        return self._search_index.search(query=query, limit=limit)


# from typing import Type
# from localis.data import DTO, Model
# from localis.data.models.fields import Expression
# from localis.search import FuzzySearch

# TModel = TypeVar("TModel", bound=Model)


# class Registry(Generic[TModel, TDTO], ABC):
#     """Abstract base registry class defining interface for lookup and search."""

#     ID_FIELDS: tuple[str] = ()

#     SEARCH_FIELD_WEIGHTS: dict[str, float] = {}
#     SEARCH_ORDER_FIELDS: list[str] = []
#     """Override to provide the fields for search scoring."""

#     def __init__(self, model_cls: Type[TModel]):
#         self._model_cls: Type[TModel] = model_cls
#         self._count: int | None = None
#         self._cache: list[TDTO] = None
#         self._order_by: str = ""
#         self._addl_search_attrs: list[str] = []


#     @property
#     def count(self) -> int:
#         return self.__len__()

#     def get(self, *, id: int | None = None, **kwargs) -> TDTO | None:
#         return None

#     def filter(
#         self, query: str = None, name: str = None, limit: int = None, **kwargs
#     ) -> list[TDTO]:
#         if name:
#             kwargs["name"] = name
#         if kwargs:
#             results = self._model_cls.fts_match(
#                 field_queries=kwargs, order_by=["rank"], limit=limit
#             )
#         elif query:
#             results = self._model_cls.fts_match(query, order_by=["rank"], limit=limit)
#         else:
#             return []
#         return [r.to_dto() for r in results]

#     def search(self, query: str, limit=None, **kwargs) -> list[tuple[TDTO, float]]:
#         if not query:
#             return []

#         search = FuzzySearch(
#             query,
#             self._model_cls,
#             self.SEARCH_FIELD_WEIGHTS,
#             self.SEARCH_ORDER_FIELDS,
#             limit,
#         )

#         return search.run()

#     def _sort_matches(self, matches: list, limit: int) -> list[TDTO]:
#         return [
#             (row_data.dto, score)
#             for row_data, score in sorted(matches, key=lambda r: r[1], reverse=True)[
#                 :limit
#             ]
#         ]
