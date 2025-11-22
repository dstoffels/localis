# Search Engine for registries.

from localis.data import Model
from localis.dtos import DTO
from abc import abstractmethod, ABC


class SearchEngine(ABC):
    MAX_ITERATIONS = 8
    MIN_TOKEN_LEN = 1
    MATCH_THRESHOLD = 0.6
    STRONG_MATCH_THRESHOLD = 0.85
    FTS_HARD_LIMIT = 2000

    def __init__(
        self,
        query: str,
        model_cls: type[Model],
        field_weights: dict[str, float],
        orderby_fields: list[str],
        limit: int = None,
    ):
        self.query: str = query.lower()
        self.tokens = self.query.split()
        self.model_cls: type[Model] = model_cls
        self.field_weights: dict[str, float] = field_weights
        self.orderby_fields: list[str] = orderby_fields
        self.limit: int | None = limit

        self._max_score = sum(field_weights.values())
        self._iterations = max(len(t) for t in self.tokens)

        self._scored: set[int] = set()
        self._matches: dict[Model, float] = {}
        self._iteration_match_counts = [0]
        self._has_strong_match = False

    def run(self) -> list[tuple[DTO, float]]:
        self.main()
        return self.results

    def main(self):
        candidates = self._fetch_candidates(exact=True)

        for i in range(1, self._iterations + 1):
            self._score_candidates(candidates)

            if self._should_exit_early(i):
                break

            self._truncate_tokens()

            candidates = self._fetch_candidates(i)

    def _fetch_candidates(self, i: int = None, exact=False) -> list[Model]:
        if i is None:
            limit = None
        else:
            if i == self._iterations - 1:
                limit = self.FTS_HARD_LIMIT
            else:
                limit = min(self.FTS_HARD_LIMIT, i * 400)

        fts_q = " ".join(self.tokens)

        order_by = ["rank"] if exact or i == self._iterations - 2 else []

        return self.model_cls.fts_match(
            fts_q, exact_match=exact, limit=self.FTS_HARD_LIMIT, order_by=order_by
        )

    def _score_candidates(self, candidates: list[Model]):
        for c in candidates:
            if c.id not in self._scored:
                score = self.score_candidate(c)
                if score >= self.MATCH_THRESHOLD:
                    self._matches[c] = score
                if score >= self.STRONG_MATCH_THRESHOLD:
                    self._has_strong_match = True
                self._scored.add(c.id)

    def _should_exit_early(self, i):
        if i == self._iterations:
            return True

        # Did we get a strong match?
        if self._has_strong_match:
            return True

        # Did the last two iteration produce a significant number of new matches?
        prev_idx = i - 1
        prev_match_count = self._iteration_match_counts[prev_idx]

        new_match_count = len(self._matches) - prev_match_count
        self._iteration_match_counts.append(new_match_count)

        if prev_match_count == 0:
            return False

        if i >= 3 and sum(self._iteration_match_counts[-2:]) <= 1:
            return True

        return False

    @abstractmethod
    def score_candidate(self, candidate: Model) -> float:
        return 0.0

    def _truncate_tokens(self) -> None:
        self.tokens = [
            t[:-1] if len(t) > self.MIN_TOKEN_LEN else t for t in self.tokens
        ]

    @property
    def results(self) -> list[tuple[DTO, float]]:
        return sorted(
            [(m.to_dto(), score) for m, score in self._matches.items()],
            key=lambda x: (x[1], *[getattr(x[0], f) for f in self.orderby_fields]),
            reverse=True,
        )[: self.limit]
