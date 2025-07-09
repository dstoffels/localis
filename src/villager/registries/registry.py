from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from ..db.models import DTOModel
from typing import Type, NamedTuple, Dict
from peewee import prefetch
from ..types import DTOBase
from villager.db import db
from villager.utils import normalize
from rapidfuzz import fuzz

TModel = TypeVar("TModel", bound=DTOModel)
TDTO = TypeVar("TDTO", bound=DTOBase)


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

    def __init__(self, model_cls: Type[TModel], dto_cls: Type[TDTO]):
        self._model_cls: Type[TModel] = model_cls
        self._dto_cls: Type[TDTO] = dto_cls
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
        return self._fuzzy_search(query, limit)

    @abstractmethod
    def _build_sql(self) -> str:
        return ""

    def _query_fts(self, fts_query: str, limit=100) -> list[TDTO]:
        cursor = db.execute_sql(
            self._build_sql(),
            (fts_query, limit),
        )
        return [self._dto_cls.from_row(r) for r in cursor]

    def _fuzzy_search(self, query: str, limit: int = 5) -> list[TDTO]:
        norm_query = normalize(query)
        tokens = norm_query.split(" ")

        matches: dict[str, tuple[TDTO, float]] = {}

        tokens_len = sum([len(t) for t in tokens])

        while tokens_len > len(tokens) and len(matches) < limit:
            fts_q = " ".join([f"{t}*" for t in tokens])
            results: list[TDTO] = self._query_fts(fts_q, limit=100)
            for r in results:
                score = fuzz.token_sort_ratio(query, r.name) / 100

                matches[r.name] = (r, score)

            tokens_len = 0
            for i, t in enumerate(tokens):
                if len(t) <= 1:
                    continue
                tokens[i] = t[:-1]
                tokens_len += len(t)

        return sorted(matches.values(), key=lambda x: x[1], reverse=True)[:limit]

    def _load_cache(self, *related_models: Type[DTOModel]):
        self._cache = Cache(self._model_cls).load(*related_models)
