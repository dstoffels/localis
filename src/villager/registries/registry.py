from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from typing import Type, NamedTuple, Dict
from ..db.dtos import DTOBase
from villager.db import db
from villager.utils import normalize
from rapidfuzz import fuzz
from concurrent.futures import ThreadPoolExecutor, as_completed

TModel = TypeVar("TModel")
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

    def load(self, *related_models) -> "Cache[TModel, TDTO]":
        """Prefetch model and related models, and populate the cache."""
        # base_query = self.model_cls.select()
        # prefetch_query: Iterator[TModel] = prefetch(base_query, *related_models)

        # for m in prefetch_query:
        #     self[m.id] = CacheItem(m, m.to_dto())

        # return self
        pass


class Registry(Generic[TModel, TDTO], ABC):
    """Abstract base registry class defining interface for lookup and search."""

    def __init__(self, model_cls: Type[TModel], dto_cls: Type[TDTO]):
        self._model_cls: Type[TModel] = model_cls
        self._dto_cls: Type[TDTO] = dto_cls
        self._count: int | None = None
        self._cache: Cache[TModel, TDTO] | None = None
        self._sql_filter: str = ""
        self._sql_filter_appendix: str = ""
        self._update_candidates: bool = True

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
    def search(self, query: str, limit=100, **kwargs) -> list[TDTO]:
        return []

    @property
    def _sql_filter_base(self) -> str:
        return ""

    def _build_sql_query(self) -> None:
        self._sql_filter = self._sql_filter_base + self._sql_filter_appendix

    def _build_fts_query(self, query: str, limit=100) -> str:
        tokens = query.split(" ")
        fts_q = " ".join([f"{t}*" for t in tokens])
        self._sql_filter_appendix = (
            f"""WHERE f.tokens MATCH "{fts_q}" ORDER BY rank LIMIT {limit}"""
        )
        self._build_sql_query()

    def _filter_candidates(self) -> list[tuple[int, TDTO, str]]:
        """Returns a list of (id, dto, fts_tokens) tuples for candidates."""
        cursor = db.execute_sql(self._sql_filter)
        return [(r[0], self._dto_cls.from_row(r), r[len(r) - 1]) for r in cursor]

    def _score(self, norm_query: str, fts_tokens: str, threshold=0.6) -> float:
        """Scores a query against a FTS token string."""
        q_tokens = norm_query.split()
        f_tokens = fts_tokens.split()
        q_len = len(q_tokens)
        f_len = len(f_tokens)

        match_scores = []

        # Score each query token against all FTS tokens, collect best match
        for qt in q_tokens:
            best = max(fuzz.ratio(qt, ft) for ft in f_tokens) / 100
            if best >= threshold:
                match_scores.append(best)

        if not match_scores:
            return 0.0

        avg_weight = 0.7
        coverage_weight = 1 - avg_weight

        # avg per query token
        avg_match_score = avg_weight * (sum(match_scores) / q_len)

        # fraction of FTS tokens matched
        coverage = coverage_weight * len(match_scores) / f_len if f_tokens else 0

        return avg_match_score + coverage

    def _fuzzy_search(self, norm_query: str, limit: int) -> list[TDTO]:
        tokens = norm_query.split(" ")

        matches: dict[int, tuple[TDTO, float]] = {}

        candidates = self._filter_candidates()

        while len(matches) < limit:
            for id, r, fts_tokens in candidates:
                if id in matches:
                    continue
                score = self._score(norm_query, fts_tokens)

                if score > 0.4:
                    matches[id] = (r, score)

            if all(len(t) <= 1 for t in tokens):
                break

            for i, t in enumerate(tokens):
                t_len = len(t)
                if t_len > 2:
                    tokens[i] = t[:-2]
                elif t_len > 1:
                    tokens[i] = t[:-1]

            if self._update_candidates:
                self._build_fts_query(" ".join(tokens))
                candidates = self._filter_candidates()

        return sorted(matches.values(), key=lambda x: x[1], reverse=True)[:limit]

    def _load_cache(self, *related_models):
        self._cache = Cache(self._model_cls).load(*related_models)
