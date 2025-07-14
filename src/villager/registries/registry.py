from typing import Iterator, Generic, TypeVar
from abc import abstractmethod, ABC
from typing import Type, Callable
from villager.db import db, DTO, Model, RowData
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

    def search(self, query: str, limit=5, **kwargs) -> list[TDTO]:
        if not query:
            return []

        norm_query = normalize(query)
        tokens = norm_query.split()
        min_len = len(tokens) * 2
        total_tok_len = sum(len(t) for t in tokens)

        # exact match on initial query unless overridden
        candidates = self._model_cls.fts_match(norm_query, limit, exact=True)

        matches: dict[int, tuple[TDTO, float]] = {}
        found_exact_match = False

        MAX_ITERATIONS = 100

        for step in range(MAX_ITERATIONS):

            results = process.extract(
                norm_query,
                choices=[c.tokens for c in candidates],
                scorer=fuzz.partial_token_set_ratio,
                limit=None,
            )

            for _, score, idx in results:
                candidate = candidates[idx]
                if score >= 100:
                    found_exact_match = True
                matches[candidate.id] = (candidate.dto, score)

            if (
                found_exact_match
                or len(matches) >= limit * 2
                or total_tok_len <= min_len
            ):
                break

            # truncate tokens and generate next FTS query
            new_tokens = []
            total_tok_len = 0
            for t in tokens:
                new_len = max(2, len(t) - step)
                new_tokens.append(t[:new_len])
                total_tok_len += new_len
            fts_q = " ".join(new_tokens)

            candidates = self._model_cls.fts_match(fts_q)

        return [
            dto
            for dto, score in sorted(
                matches.values(), key=lambda r: r[1], reverse=True
            )[:limit]
        ]
