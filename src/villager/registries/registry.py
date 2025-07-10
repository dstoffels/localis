from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from ..db.models import DTOModel
from typing import Type, NamedTuple, Dict
from peewee import prefetch
from ..types import DTOBase
from villager.db import db
from villager.utils import normalize
from rapidfuzz import fuzz
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    def _build_sql(self) -> str:
        return ""

    def _query_fts(self, fts_query: str, limit=100) -> list[tuple[TDTO, str]]:
        cursor = db.execute_sql(
            self._build_sql(),
            (fts_query, limit),
        )
        return [(self._dto_cls.from_row(r), r[len(r) - 1]) for r in cursor]

    def _score(self, norm_query: str, fts_tokens: str, threshold=0.7) -> float:
        q_tokens = norm_query.split()
        f_tokens = fts_tokens.split()
        q_len = len(q_tokens)
        f_len = len(f_tokens)

        match_scores = []

        # Score each query token against all FTS tokens, collect best match & index
        for qt in q_tokens:
            best = max(fuzz.ratio(qt, ft) for ft in f_tokens) / 100
            if best >= threshold:
                match_scores.append(best)

        if not match_scores:
            return 0.0

        # avg per query token
        avg_match_score = 0.7 * (sum(match_scores) / q_len)

        # fraction of FTS tokens matched
        coverage = 0.3 * len(match_scores) / f_len if f_tokens else 0

        return avg_match_score + coverage

    def _fuzzy_search(self, query: str, limit: int = 5) -> list[TDTO]:
        norm_query = normalize(query)
        tokens = norm_query.split(" ")

        matches: dict[int, tuple[TDTO, float]] = {}

        while len(matches) < limit:

            fts_q = " ".join([f"{t}*" for t in tokens])
            results = self._query_fts(fts_q, limit=100)

            for r, fts_tokens in results:
                if r.id in matches:
                    continue
                score = self._score(norm_query, fts_tokens)

                if score > 0.4:
                    matches[r.id] = (r, score)

            if all(len(t) <= 1 for t in tokens):
                break

            for i, t in enumerate(tokens):
                if len(t) > 1:
                    tokens[i] = t[:-1]

        return sorted(matches.values(), key=lambda x: x[1], reverse=True)[:limit]

    def _load_cache(self, *related_models: Type[DTOModel]):
        self._cache = Cache(self._model_cls).load(*related_models)
