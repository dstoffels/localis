from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from peewee import SqliteDatabase
from ..db.models import DTOModel
from typing import Type, NamedTuple, Dict
from peewee import prefetch, Model

TModel = TypeVar("TModel", bound=DTOModel)
TDTO = TypeVar("TDTO")


class CacheItem(NamedTuple, Generic[TModel, TDTO]):
    """Cache item for a registry entry."""

    model: TModel
    dto: TDTO


class Cache(Dict[int, CacheItem[TModel, TDTO]]):
    """Cache for registry entries."""

    def __init__(self, model: Type[TModel]):
        super().__init__()
        self.model_cls: Type[TModel] = model

    def load(self, *related_models: Type[DTOModel]) -> "Cache[TModel, TDTO]":
        """Prefetch model and related models, and populate the cache."""
        base_query = self.model_cls.select()
        prefetch_query: Iterator[TModel] = prefetch(base_query, *related_models)

        for m in prefetch_query:
            self[m.id] = CacheItem(m, m.to_dto())

        return self


class Registry(Generic[TModel, TDTO], ABC):
    """Abstract base registry class defining interface for lookup and search."""

    def __init__(self, model: Type[TModel]):
        self._model_cls: Type[TModel] = model
        self._count: int | None = None
        self._cache: Cache[TModel, TDTO] | None = None

    def __iter__(self) -> Iterator[TDTO]:
        return (item.dto for item in self.cache.values())

    def __getitem__(self, index: int) -> TDTO:
        return self.cache.values()[index].to_dto()

    def __len__(self) -> int:
        if self._count is None:
            self._count = self._model_cls.select().count()
        return self._count

    @property
    def count(self) -> int:
        return self.__len__()

    @property
    def cache(self) -> Cache[TModel, TDTO]:
        if self._cache is None:
            self._load_cache()
        return self._cache

    @abstractmethod
    def get(self, identifier: str | int) -> TDTO | None:
        return None

    @abstractmethod
    def lookup(self, identifier: str) -> list[TDTO]:
        return []

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[tuple[TDTO, float]]:
        return []

    def _load_cache(self, *related_models: Type[DTOModel]):
        self._cache = Cache(self._model_cls).load(*related_models)
