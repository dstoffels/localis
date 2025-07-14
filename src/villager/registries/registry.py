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
        self._candidates: list[RowData[TDTO]] = []
        self._addl_fts_clause: str = ""

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

    def _fts_match(self, query: str, limit=100, exact=False) -> None:
        self._candidates = self._model_cls.fts_match(
            query, limit, exact, addl_clause=self._addl_fts_clause
        )

    def search(self, query: str, limit=5, **kwargs) -> list[TDTO]:
        if not query:
            return []

        norm_query = normalize(query)
        tokens = norm_query.split()
        min_len = len(tokens) * 2
        total_tok_len = sum(len(t) for t in tokens)

        # exact match on initial query unless overridden
        self._fts_match(norm_query, limit, exact=True)

        matches: dict[int, tuple[TDTO, float]] = {}
        found_exact_match = False

        MAX_ITERATIONS = 100

        for step in range(MAX_ITERATIONS):

            results = process.extract(
                norm_query,
                choices=[c.tokens for c in self._candidates],
                scorer=fuzz.partial_token_set_ratio,
                limit=None,
            )

            for _, score, idx in results:
                candidate = self._candidates[idx]
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

            self._fts_match(fts_q)

        return [
            dto
            for dto, score in sorted(
                matches.values(), key=lambda r: r[1], reverse=True
            )[:limit]
        ]

        # tokens = norm_query.split(" ")

        # matches: dict[int, tuple[TDTO, float]] = {}

        # while len(matches) < limit:
        #     best_matches = process.extract(
        #         norm_query,
        #         choices=[c.tokens for c in self._search_candidates],
        #         scorer=fuzz.WRatio,
        #         limit=limit,
        #     )

        #     matches.update(
        #         {
        #             self._search_candidates[i].id: self._search_candidates[i].dto
        #             for _, _, i in best_matches
        #             if self._search_candidates[i].id not in matches
        #         }
        #     )

        #     if all(len(t) <= 1 for t in tokens):
        #         break

        #     for i, t in enumerate(tokens):
        #         t_len = len(t)
        #         if t_len > 3:
        #             tokens[i] = t[:-3]
        #         elif t_len > 1:
        #             tokens[i] = t[:-1]

        #     q = " ".join(tokens)

        #     if self._use_fts_match:
        #         self._search_candidates = self._model_cls.fts_match(q, limit=limit * 5)

        # return sorted(matches.values(), key=lambda x: x[1], reverse=True)[:limit]

        while len(matches) < limit:
            for id, dto, fts_tokens, _ in self._candidates:
                if id in matches:
                    continue
                score = self._score(norm_query, fts_tokens)

                if score > 0.4:
                    matches[id] = (dto, score)
        # best = process.extract(
        #     norm_query,
        #     choices=[c.tokens for c in self._search_candidates],
        #     scorer=fuzz.WRatio,
        #     limit=limit,
        #     score_cutoff=90,
        # )

        # return [(self._search_candidates[i].dto, score / 100) for _, score, i in best]

    # def _score(self, norm_query: str, fts_tokens: str, threshold=0.6) -> float:
    #     """Scores a query against a FTS token string."""

    #     q_tokens = norm_query.split()
    #     f_tokens = fts_tokens.split()
    #     POSITION_WEIGHT = 0.2

    #     match_scores = []
    #     matched_fts = set()

    #     # Score each query token against all FTS tokens, collect best match
    #     for qi, qt in enumerate(q_tokens):
    #         best_score = 0
    #         best_idx = None
    #         for fi, ft in enumerate(f_tokens):
    #             if qt == ft:
    #                 score = 1.0
    #             else:
    #                 score = fuzz.ratio(qt, ft) / 100

    #             position_penalty = POSITION_WEIGHT * (
    #                 abs(qi - fi) / max(len(q_tokens), len(f_tokens))
    #             )
    #             adjusted_score = score * (1 - position_penalty)
    #             if adjusted_score > best_score:
    #                 best_score = adjusted_score
    #                 best_idx = fi

    #         if best_score >= threshold and best_idx is not None:
    #             match_scores.append(best_score)
    #             matched_fts.add(best_idx)

    #     if not match_scores:
    #         return 0.0

    #     avg_weight = 0.7
    #     coverage_weight = 1 - avg_weight

    #     # avg per query token
    #     avg_match_score = avg_weight * (sum(match_scores) / len(q_tokens))

    #     # fraction of FTS tokens matched
    #     coverage = coverage_weight * len(matched_fts) / len(f_tokens) if f_tokens else 0

    #     return avg_match_score + coverage
