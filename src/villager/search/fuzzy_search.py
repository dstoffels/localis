from villager.search.search_base import SearchBase
from rapidfuzz import fuzz
from villager.utils import normalize


class FuzzySearch(SearchBase):
    def score_candidate(self, candidate):
        score = 0.0
        for field, weight in self.field_weights.items():
            values = getattr(candidate, field, "").split("|")
            score += (
                max(fuzz.token_sort_ratio(v, self.query) for v in values) / 100 * weight
            )

        return score / self._max_score
