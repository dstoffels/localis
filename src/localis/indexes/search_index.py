from localis.models import Model, DTO
from rapidfuzz import fuzz, process
from localis.indexes.index import Index
from localis.utils import normalize, generate_trigrams, decode_id_list
import math
import heapq


class SearchIndex(Index):
    def __init__(
        self,
        model_cls,
        cache,
        filepath,
        noise_threshold=0.6,
        penalty_factor=0.15,
        **kwargs,
    ):
        self.NOISE_THRESHOLD = noise_threshold
        self.PENALITY_FACTOR = penalty_factor
        super().__init__(model_cls, cache, filepath, **kwargs)

    def load(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    trigram, ids_str = line.split("\t")
                    ids = set(decode_id_list(ids_str))
                    self.index[trigram] = ids
        except Exception as e:
            raise Exception(f"Failed to load search index from {filepath}: {e}")

    def search(self, query: str, limit=10):
        if not query:
            return []

        self.query = normalize(query)
        self.query_trigrams = set(generate_trigrams(self.query))

        candidates = self._get_candidates()

        if not candidates:
            return []

        results = self.score_candidates(candidates)
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:limit]

    def _get_candidates(self, max_candidates=1000) -> set[int]:
        """Get candidate document IDs matching the query via trigrams"""
        total_docs = len(self.cache)

        # build list of (trigram, candidate_ids, idf)
        trigram_list: list[tuple[str, set[int], float]] = []
        for trigram in generate_trigrams(self.query):
            cands = self.index.get(trigram)
            if not cands:
                continue
            df = len(cands)
            idf = math.log((total_docs + 1) / (df + 1))
            trigram_list.append((trigram, cands, idf))

        if not trigram_list:
            return set()

        trigram_list.sort(key=lambda x: x[2], reverse=True)

        candidates = set()
        for trigram, cands, _ in trigram_list:
            candidates.update(cands)
            if len(candidates) >= max_candidates:
                break

        # aggregate scores for each candidate document
        if len(candidates) > max_candidates:
            scores: dict[int, float] = {}
            for trigram, cands, idf in trigram_list:
                for id in cands:
                    if id in candidates:
                        scores[id] = scores.get(id, 0.0) + idf

            top = heapq.nlargest(max_candidates, scores.items(), key=lambda x: x[1])
            return {id for id, _ in top}
        return candidates

    FIELD_SCORE_WEIGHT = 0.7
    CONTEXT_SCORE_WEIGHT = 0.3

    def _score_trigrams(self, candidate: Model) -> float:
        """Score candidate based on trigram overlap with the query"""
        query_trigrams = self.query_trigrams
        candidate_trigrams = set(candidate.search_tokens.split("|"))
        overlap = len(query_trigrams & candidate_trigrams)
        return overlap / len(query_trigrams) if query_trigrams else 0.0

        intersection = query_trigrams.intersection(candidate_trigrams)
        union = query_trigrams.union(candidate_trigrams)

        return len(intersection) / len(union)

    def score_candidates(self, candidates: set[int]) -> list[tuple[DTO, float]]:
        """Score candidate documents based on field matches and context similarity"""

        query_tokens = self.query.split()
        results = []

        for id in candidates:
            candidate = self.cache[id]

            if fuzz.ratio(self.query, candidate.name.lower()) < 50:
                continue

            context_score = (
                (fuzz.token_ratio(self.query, candidate.search_context) / 100.0)
                if candidate.search_context and len(query_tokens) > 2
                else 1.0
            )

            field_score = self._score_fields(candidate)

            final_score = (
                field_score * self.FIELD_SCORE_WEIGHT
                + context_score * self.CONTEXT_SCORE_WEIGHT
            )

            if final_score > self.NOISE_THRESHOLD:
                results.append((candidate.dto, final_score))

        return results

    def _score_fields(self, candidate: Model) -> float:
        score = 0.0
        match_weights = 0.0

        for field, weight in candidate.search_values:
            if isinstance(field, list):
                matches = process.extract(
                    self.query,
                    field,
                    scorer=fuzz.WRatio,
                    score_cutoff=60,
                    limit=None,
                )
                field_score = (
                    max(score for _, score, _ in matches) / 100.0 if matches else 0.0
                )
            else:
                field_score = fuzz.WRatio(self.query, field) / 100.0

            # Only consider significant matches
            if field_score >= self.NOISE_THRESHOLD:
                score += field_score * weight
                match_weights += weight
            else:
                # small penalty for non-matching fields for tie breaking
                penalty = (
                    (self.NOISE_THRESHOLD - field_score) * self.PENALITY_FACTOR * weight
                )
                score -= penalty

        return score / match_weights if match_weights > 0 else 0.0

    REMOVE_CHARS = (",", ".")

    def normalize(self, text: str) -> str:
        norm = normalize(text)

        trans_table = str.maketrans("", "", "".join(self.REMOVE_CHARS))
        return norm.translate(trans_table)
