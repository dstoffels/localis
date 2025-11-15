# Search Engine for registries.

from villager.db import Model
from villager.utils import normalize
from villager.dtos import DTO
from abc import abstractmethod, ABC


class SearchBase(ABC):
    MAX_ITERATIONS = 10
    MIN_TOKEN_LEN = 2
    SCORE_THRESHOLD = 1.5

    def __init__(
        self,
        query: str,
        model_cls: type[Model],
        field_weights: dict[str, float],
        limit: int = None,
    ):
        self.query: str = normalize(query)
        self.tokens = self.query.split()
        self.model_cls: type[Model] = model_cls
        self.field_weights: dict[str, float] = field_weights
        self.limit: int | None = limit

        # hold a map of seen candidates to prevent repeated scoring
        self._scored: dict[int, Model] = {}
        self._matches: dict[Model, float] = {}

    def run(self) -> list[tuple[DTO, float]]:
        self.main()
        return self.results

    def main(self):
        # run loop until no new, acceptable fuzzy matches are produced from fts candidates?
        candidates = self._fetch_candidates(exact=True)

        for i in range(self.MAX_ITERATIONS):
            self._score_candidates(candidates)
            if self._tokens_exhausted() or self._at_limit():
                break

            self._truncate_tokens()
            candidates = self._fetch_candidates()

    def _fetch_candidates(self, exact=False) -> list[Model]:
        tokens_exhausted = self._tokens_exhausted()
        order_by = ["rank"] if tokens_exhausted else []
        limit = 1000 if tokens_exhausted else None
        fts_q = " ".join(self.tokens)
        return self.model_cls.fts_match(
            fts_q, exact_match=exact, limit=limit, order_by=order_by
        )

    def _score_candidates(self, candidates: list[Model]):
        for c in candidates:
            if c.id in self._scored:
                continue
            score = self.score_candidate(c)
            if score >= self.SCORE_THRESHOLD:
                self._matches[c] = score
            self._scored[c.id] = c

    @abstractmethod
    def score_candidate(self, candidate: Model) -> float:
        return 0.0

    def _truncate_tokens(self) -> None:
        self.tokens = [
            t[:-1] if len(t) > self.MIN_TOKEN_LEN else t for t in self.tokens
        ]

    def _at_limit(self) -> bool:
        if self.limit is not None:
            return len(self._matches) >= self.limit
        return False

    def _tokens_exhausted(self) -> bool:
        return all(len(t) <= self.MIN_TOKEN_LEN for t in self.tokens)

    @property
    def results(self) -> list[tuple[DTO, float]]:
        # TODO: supplement with weak matches if len(strong_matches) < limit
        return sorted(
            [(m.to_dto(), score) for m, score in self._matches.items()],
            key=lambda x: x[1],
            reverse=True,
        )[: self.limit]
