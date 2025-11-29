from localis.data.model import Model
from collections import defaultdict
from rapidfuzz import fuzz
from localis.utils import normalize, generate_trigrams
import re


class SearchEngine:
    def __init__(self, cache: dict[int, Model]):
        self.cache = cache
        self.index: dict[str, set[int]] = defaultdict(set)

        # Index name tokens only
        for id, model in cache.items():
            for token in model.name.lower().split():
                if len(token) <= 3:
                    # Shorties: exact match
                    self.index[token].add(id)
                else:
                    # Long tokens: trigrams
                    for i in range(len(token) - 2):
                        trigram = token[i : i + 3]
                        self.index[trigram].add(id)

    def search(self, query: str, threshold=0.6, limit=10):
        if not query:
            return []

        self.query = self.normalize(query)
        tokens = query.split()

        if not tokens:
            return []

        candidates = self._get_candidates(tokens)

        if not candidates:
            return []

        results = self.score_candidates(candidates)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def _get_candidates(self, tokens: list[str]) -> set[int]:
        """Intersect token candidates progressively until intersection is empty"""
        candidates = None

        for i, token in enumerate(tokens):
            token_candidates = self._get_token_candidates(token)

            if candidates is None:
                candidates = token_candidates
            else:
                intersected = candidates & token_candidates

                if not intersected or len(intersected) < 100:
                    return candidates

                candidates = intersected

        return candidates if candidates else set()

    def _get_token_candidates(self, token: str) -> set[int]:
        """Get all candidates matching this token via trigrams"""
        # if len(token) <= 3:
        #     return self.index.get(token, set())
        # candidates = set()

        # short circuit exact token match
        candidates = self.index.get(token, set())
        if not candidates:
            for trigram in generate_trigrams(token):
                candidates |= self.index.get(trigram, set())

        return candidates

    def score_candidates(self, candidates: set[int]):
        NOISE_THRESHOLD = 0.6

        print("candidate cnt", len(candidates))

        results = []

        for id in candidates:
            score = 0.0
            candidate = self.cache[id]

            for field in candidate.search_fields:
                field_score = fuzz.WRatio(self.query, field) / 100
                if field_score >= NOISE_THRESHOLD:
                    score += field_score

            final_score = score / len(candidate.search_fields)
            if final_score > 0.0:
                results.append((candidate.dto, final_score))

        return results

    REMOVE_CHARS = (",", ".")

    def normalize(self, text: str) -> str:
        norm = normalize(text)

        trans_table = str.maketrans("", "", "".join(self.REMOVE_CHARS))
        return norm.translate(trans_table)
