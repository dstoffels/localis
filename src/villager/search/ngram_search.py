from villager.search.search_engine import SearchEngine
from villager.data import Model

from villager.dtos import DTO


class NgramSearch(SearchEngine):
    SCORE_THRESHOLD = 0.5
    NGRAM_LEN = 2

    def __init__(self, query, model_cls, field_weights, limit=None):
        # split query into tokens and ngram each one
        self.q_token_ngrams: list[set[str]] = [
            self._ngram(t, self.NGRAM_LEN) for t in query.split(" ")
        ]
        super().__init__(query, model_cls, field_weights, limit)

    def score_candidate(self, candidate: Model) -> float:
        score = 0.0

        f_token_map: dict[str, tuple[set[str], float]] = {}

        for field, weight in self.field_weights.items():
            value = getattr(candidate, field, "")
            for token in value.replace("|", " ").split():
                if token not in f_token_map:
                    f_token_map[token] = (self._ngram(token), weight)

        for q_token_ngram in self.q_token_ngrams:
            for f_token_ngrams, weight in f_token_map.values():
                if not q_token_ngram or not f_token_ngrams:
                    continue
                score += self._score_ngrams(q_token_ngram, f_token_ngrams) * weight

        return score

    def _score_ngrams(self, q_token_ngram: set[str], token_ngrams: set[str]) -> float:
        return len(q_token_ngram & token_ngrams) / len(q_token_ngram | token_ngrams)

    def _ngram(self, s: str, n: int = 2) -> set[str]:
        s = s.lower().replace(" ", "")
        return {s[i : i + n] for i in range(len(s) - n + 1)}
