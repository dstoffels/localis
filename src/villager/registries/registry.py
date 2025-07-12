from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from typing import Type, Callable
from villager.db import db, DTO, Model, RowData
from villager.utils import normalize
from rapidfuzz import fuzz
from concurrent.futures import ThreadPoolExecutor, as_completed

TModel = TypeVar("TModel", bound=Model)
TDTO = TypeVar("TDTO", bound=DTO)


class Registry(Generic[TModel, TDTO], ABC):
    """Abstract base registry class defining interface for lookup and search."""

    def __init__(self, model_cls: Type[TModel]):
        self._model_cls: Type[TModel] = model_cls
        self._count: int | None = None
        self._cache: list[TDTO] = None
        self._search_candidates: list = []
        self._use_fts_match: bool = True

    def __iter__(self) -> Iterator[TDTO]:
        return iter(self.cache)

    def __getitem__(self, index: int | slice) -> TDTO | list[TDTO]:
        return self.cache[index]

    def __len__(self) -> int:
        if self._count is None:
            self._count = self._model_cls.count()
        return self._count

    @property
    def count(self) -> int:
        return self.__len__()

    @property
    def cache(self) -> list[TDTO]:
        if self._cache is None:
            self._cache = [r.dto for r in self._model_cls.select()]
        return self._cache

    @abstractmethod
    def get(self, identifier: str | int) -> TDTO | None:
        return None

    @abstractmethod
    def lookup(self, identifier: str, **kwargs) -> list[TDTO]:
        return []

    @abstractmethod
    def search(self, query: str, limit=100, **kwargs) -> list[TDTO]:
        return []

    # def _filter_candidates(self, norm_query: str) -> list[tuple[int, TDTO, str]]:
    #     """Returns a list of (id, dto, fts_tokens) tuples for candidates."""
    #     if self._update_candidates:
    #         self._search_candidates = self._model_cls.fts_match(norm_query)

    def _score(self, norm_query: str, fts_tokens: str, threshold=0.6) -> float:
        """Scores a query against a FTS token string."""

        q_tokens = norm_query.split()
        f_tokens = fts_tokens.split()
        POSITION_WEIGHT = 0.2

        match_scores = []
        matched_fts = set()

        # Score each query token against all FTS tokens, collect best match
        for qi, qt in enumerate(q_tokens):
            best_score = 0
            best_idx = None
            for fi, ft in enumerate(f_tokens):
                if qt == ft:
                    score = 1.0
                else:
                    score = fuzz.ratio(qt, ft) / 100

                position_penalty = POSITION_WEIGHT * (
                    abs(qi - fi) / max(len(q_tokens), len(f_tokens))
                )
                adjusted_score = score * (1 - position_penalty)
                if adjusted_score > best_score:
                    best_score = adjusted_score
                    best_idx = fi

            if best_score >= threshold and best_idx is not None:
                match_scores.append(best_score)
                matched_fts.add(best_idx)

        if not match_scores:
            return 0.0

        avg_weight = 0.7
        coverage_weight = 1 - avg_weight

        # avg per query token
        avg_match_score = avg_weight * (sum(match_scores) / len(q_tokens))

        # fraction of FTS tokens matched
        coverage = coverage_weight * len(matched_fts) / len(f_tokens) if f_tokens else 0

        return avg_match_score + coverage

    def _fuzzy_search(self, norm_query: str, limit: int) -> list[TDTO]:
        tokens = norm_query.split(" ")

        matches: dict[int, tuple[TDTO, float]] = {}

        while len(matches) < limit:
            for id, dto, fts_tokens, _ in self._search_candidates:
                if id in matches:
                    continue
                score = self._score(norm_query, fts_tokens)

                if score > 0.4:
                    matches[id] = (dto, score)

            if all(len(t) <= 1 for t in tokens):
                break

            for i, t in enumerate(tokens):
                t_len = len(t)
                if t_len > 2:
                    tokens[i] = t[:-2]
                elif t_len > 1:
                    tokens[i] = t[:-1]

            q = " ".join(tokens)
            if self._use_fts_match:
                self._search_candidates = self._model_cls.fts_match(q)

        return sorted(matches.values(), key=lambda x: x[1], reverse=True)[:limit]
