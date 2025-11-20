from villager.search.search_engine import SearchEngine
from rapidfuzz import fuzz, process


class FuzzySearch(SearchEngine):
    NOISE_THRESHOLD = 0.6

    def score_candidate(self, candidate):
        score = 0.0
        total_matched_weight = 0.0

        for field, weight in self.field_weights.items():
            fvalue = getattr(candidate, field, "")
            if fvalue:
                values = fvalue.lower().split("|")
                matches = process.extract(
                    self.query,
                    values,
                    scorer=fuzz.token_set_ratio,
                    score_cutoff=60,
                )
                field_score = (
                    max(score for _, score, i in matches) / 100 if matches else 0.0
                )

                # # Filter noise
                if field_score >= self.NOISE_THRESHOLD:
                    score += field_score * weight
                    total_matched_weight += weight
        return score / total_matched_weight if total_matched_weight > 0 else 0.0
