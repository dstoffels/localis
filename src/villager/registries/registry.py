from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from typing import Type, Callable
from villager.db import db, DTO, Model
from villager.utils import normalize
from rapidfuzz import fuzz, process
from concurrent.futures import ThreadPoolExecutor, as_completed

TModel = TypeVar("TModel", bound=Model)
TDTO = TypeVar("TDTO", bound=DTO)


class Registry(Generic[TModel, TDTO], ABC):
    """Abstract base registry class defining interface for lookup and search."""

    def __init__(self, model_cls: Type[TModel]):
        self._model_cls: Type[TModel] = model_cls
        self._count: int | None = None
        self._cache: list[TDTO] = None
        self._order_by: str = ""
        self._addl_search_attrs: list[str] = []

    @property
    def cache(self):
        if self._cache is None:
            self._cache = [m.to_dto() for m in self._model_cls.select()]
        return self._cache

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

    @abstractmethod
    def get(self, *, id: int | None = None) -> TDTO | None:
        """Exact lookup by unique identifiers, must provide keyword args for the identifier."""
        return None

    def lookup(self, query: str, limit: int | None = None) -> list[TDTO]:
        """Exact-match lookup of an input query across all fields. Returns a list of exact-matched entries."""
        results = self._model_cls.fts_match(
            query, limit, order_by=["rank"], exact_match=True
        )

        return [r.to_dto() for r in results]

    def search(self, query: str, limit=5, **kwargs) -> list[TDTO]:
        """"""
        if not query:
            return []

        norm_query = normalize(query)
        tokens = norm_query.split()
        min_len = len(tokens) if len(tokens) > 1 else 2
        total_tok_len = sum(len(t) for t in tokens)

        MAX_ITERATIONS = 20
        NAME_WEIGHT = 0.7
        TOKEN_WEIGHT = 0.3

        matches: dict[int, tuple[TDTO, float]] = {}

        # exact match on initial query unless overridden
        candidates: list[RowData[TDTO]] = self._model_cls.fts_match(
            norm_query, exact_match=True, order_by=self._order_by
        )

        for step in range(MAX_ITERATIONS):
            results = process.extract(
                norm_query,
                choices=[c.search_tokens for c in candidates],
                scorer=fuzz.WRatio,
                limit=None,
            )

            for _, token_score, idx in results:
                candidate = candidates[idx]
                name_score = fuzz.ratio(norm_query, candidate.dto.name)

                # consider additional attributes for scoring. uses name weighting on the highest score found betwen name and additional attrs
                for attr in self._addl_search_attrs:
                    attr_value = getattr(candidate.dto, attr, None)
                    if attr_value:
                        attr_score = fuzz.ratio(norm_query, normalize(attr_value))
                        if attr_score > name_score:
                            name_score = attr_score

                score = name_score * NAME_WEIGHT + token_score * TOKEN_WEIGHT

                matches[candidate.id] = (candidate, score)

            # stop if we have enough matches or tokens are too short
            if len(matches) >= limit * 2 or total_tok_len <= min_len:
                break

            # truncate tokens and generate next FTS query
            new_tokens = []
            total_tok_len = 0
            for t in tokens:
                new_len = max(2, len(t) - step)
                new_tokens.append(t[:new_len])
                total_tok_len += new_len
            fts_q = " ".join(new_tokens)

            candidates = self._model_cls.fts_match(fts_q, order_by=self._order_by)

        return self._sort_matches(matches.values(), limit)

    def _sort_matches(self, matches: list, limit: int) -> list[TDTO]:
        return [
            (row_data.dto, score)
            for row_data, score in sorted(matches, key=lambda r: r[1], reverse=True)[
                :limit
            ]
        ]
