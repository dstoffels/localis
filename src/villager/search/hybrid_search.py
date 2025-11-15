from villager.search.search_base import SearchBase
from villager.db import Model
from villager.utils import normalize
from villager.dtos import DTO
from rapidfuzz import fuzz


class HybridSearch(SearchBase):
    NGRAM_LEN = 2

    def __init__(self, query, model_cls, field_weights, limit=None):
        # split query into tokens and ngram each one
        self.q_token_ngrams: list[set[str]] = [
            self._ngram(t, self.NGRAM_LEN) for t in normalize(query).split(" ")
        ]
        super().__init__(query, model_cls, field_weights, limit)

    def score_candidate(self, model: Model) -> float:
        score = 0.0

        token_map: dict[str, tuple[set[str], float]] = {}

        for field, weight in self.field_weights.items():
            value = getattr(model, field, "")
            fuzz_score = fuzz.token_set_ratio(value, self.query) / 100 * weight
            score += fuzz_score
            for token in value.replace("|", " ").split():
                if token not in token_map:
                    token_map[token] = (self._ngram(token), weight)

        for q_token_ngram in self.q_token_ngrams:
            for token_ngrams, weight in token_map.values():
                if not q_token_ngram or not token_ngrams:
                    continue
                score += self._score_ngrams(q_token_ngram, token_ngrams) * weight

        return score

    def _score_ngrams(self, q_token_ngram: set[str], token_ngrams: set[str]) -> float:
        return len(q_token_ngram & token_ngrams) / len(q_token_ngram | token_ngrams)

    def _ngram(self, s: str, n: int = 2) -> set[str]:
        s = s.lower().replace(" ", "")
        return {s[i : i + n] for i in range(len(s) - n + 1)}
