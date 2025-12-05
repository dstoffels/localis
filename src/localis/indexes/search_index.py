from localis.models import Model, DTO
from rapidfuzz import fuzz, process
from localis.indexes.index import Index
from localis.utils import normalize, generate_trigrams, decode_id_list
from collections import defaultdict


class SearchIndex(Index):
    def __init__(
        self,
        model_cls,
        cache,
        filepath,
        **kwargs,
    ):
        self.NOISE_THRESHOLD = 0.6
        self.STRONG_MATCH_THRESHOLD = 0.75
        self.PENALITY_FACTOR = 0.01
        super().__init__(model_cls, cache, filepath, **kwargs)

    def load(self, filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    trigram, ids_str = line.strip().split("\t")
                    self.index[trigram] = decode_id_list(ids_str)
        except Exception as e:
            raise Exception(f"Failed to load search index from {filepath}: {e}")

    def search(self, query: str, limit=10) -> list[tuple[DTO, float]]:
        if not query:
            return []

        self.query = self.normalize(query)
        self.match_counts: dict[int, int] = defaultdict(int)
        self.trigram_count = 0

        self._build_match_counts()

        all_results: dict[int, tuple[Model, float]] = {}
        scored_ids: set[int] = set()

        for min_trigram_matches in range(self.trigram_count, 1, -1):
            candidates = self._get_candidates(min_trigram_matches)

            new_candidates = candidates - scored_ids

            if not new_candidates:
                continue

            for id in new_candidates:
                candidate = self.cache[id]
                score = self._score_candidate(candidate)
                if score >= self.NOISE_THRESHOLD:
                    all_results[id] = (candidate, score)
                scored_ids.add(id)

            if any(
                score >= self.STRONG_MATCH_THRESHOLD
                for _, score in all_results.values()
            ):
                break

        sorted_results = sorted(all_results.values(), key=lambda x: x[1], reverse=True)
        return sorted_results[:limit]

    def _build_match_counts(self):
        index = self.index
        match_counts = self.match_counts

        for trigram in generate_trigrams(self.query):
            try:
                ids = index[trigram]
            except KeyError:
                continue

            self.trigram_count += 1
            for doc_id in ids:
                match_counts[doc_id] += 1

    def _get_candidates(self, min_matches: int):
        return {
            doc_id
            for doc_id, count in self.match_counts.items()
            if count >= min_matches
        }

    def _score_candidate(self, candidate: Model) -> float:
        score = 0.0
        total_weight = 0.0

        for i, (field_value, weight) in enumerate(candidate.get_search_values()):
            if not field_value:
                continue

            if isinstance(field_value, list):
                matches = process.extract(
                    self.query,
                    [normalize(v) for v in field_value],
                    scorer=fuzz.token_set_ratio,
                    score_cutoff=60,
                    limit=None,
                )

                field_score = (
                    max(score for _, score, _ in matches) / 100.0 if matches else 0.0
                )
            else:
                field_score = (
                    fuzz.token_set_ratio(self.query, normalize(field_value)) / 100.0
                )

            if field_score >= self.NOISE_THRESHOLD:
                score += field_score * weight
                total_weight += weight
            elif i == 0:
                # early exit if the name field is a poor match
                return 0.0
        return score / total_weight if total_weight > 0 else 0.0

    REMOVE_CHARS = (",", ".")

    def normalize(self, text: str) -> str:
        norm = normalize(text)

        trans_table = str.maketrans("", "", "".join(self.REMOVE_CHARS))
        return norm.translate(trans_table)
