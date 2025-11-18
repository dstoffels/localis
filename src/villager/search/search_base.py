# Search Engine for registries.

from villager.db import Model
from villager.utils import normalize, sanitize_fts_query
from villager.dtos import DTO
from abc import abstractmethod, ABC
from concurrent.futures import ThreadPoolExecutor


class SearchBase(ABC):
    MAX_ITERATIONS = 8
    MIN_TOKEN_LEN = 1
    SCORE_THRESHOLD = 0.35
    MATCH_THRESHOLD = 0.55

    def __init__(
        self,
        query: str,
        model_cls: type[Model],
        field_weights: dict[str, float],
        limit: int = None,
    ):
        self.query: str = query
        self.tokens = self.query.split()
        self.model_cls: type[Model] = model_cls
        self.field_weights: dict[str, float] = field_weights
        self.limit: int | None = limit

        self._max_score = sum(field_weights.values())
        self._iterations = max(len(t) for t in self.tokens) - self.MIN_TOKEN_LEN

        self._scored: set[int] = set()
        self._matches: dict[Model, float] = {}
        self._iteration_match_counts = [0]

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
            if len(candidates) == 0:
                continue

    def _fetch_candidates(self, i: int = None, exact=False) -> list[Model]:
        limit = i and i * 100
        fts_q = " ".join(self.tokens)
        fts_q = sanitize_fts_query(fts_q, exact_match=exact)

        return self.model_cls.fts_match(fts_q, exact_match=exact, limit=limit)

    def _score_candidates(self, candidates: list[Model]):
        for c in candidates:
            if c.id not in self._scored:
                score = self.score_candidate(c)
                if score >= self.SCORE_THRESHOLD:
                    self._matches[c] = score
                self._scored.add(c.id)

    def _should_exit_early(self, i):
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

    def _at_limit(self) -> bool:
        if self.limit is not None:
            return len(self._matches) >= self.limit
        return False

    @property
    def results(self) -> list[tuple[DTO, float]]:
        # TODO: supplement with weak matches if len(strong_matches) < limit
        return sorted(
            [(m.to_dto(), score) for m, score in self._matches.items()],
            key=lambda x: x[1],
            reverse=True,
        )
