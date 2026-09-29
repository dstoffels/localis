from array import array
import csv
import gzip
import logging
from pathlib import Path
import time
from typing import Generic, TypeVar
from rapidfuzz import fuzz, process
from localis.indexes.index import Index
from localis.entities import Entity
from localis.views import View
from localis.utils import normalize, generate_trigrams, decode_id_list
from collections import defaultdict

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=Entity)


class SearchIndex(Index, Generic[T]):
    def __init__(
        self,
        cache: dict[int, View[T]],
        filepath,
        **kwargs,
    ):
        self.cache = cache
        self.NOISE_THRESHOLD = 0.5
        self.STRONG_MATCH_THRESHOLD = 0.8
        self.CANDIDATE_CNT_THRESHOLD = 2000
        super().__init__(filepath, **kwargs)

    def load(self, filepath, offsets_filepath: Path, fields_filepath: Path):
        # try:
        t0 = time.perf_counter()

        self.SEARCH_FIELDS: dict[str, float] = {}
        with open(fields_filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for field, weight in reader:
                self.SEARCH_FIELDS[field] = float(weight)

        offsets: dict[str, tuple[int, int]] = {}
        with open(offsets_filepath, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            for trigram, offset, count in reader:
                offsets[trigram] = (int(offset), int(count))

        with gzip.open(filepath, "rb") as f:
            raw = f.read()

        full_array = array("I")
        full_array.frombytes(raw)

        for trigram, (offset, count) in offsets.items():
            self.index[trigram] = full_array[offset : offset + count]

        print(
            f"Loaded search index from {filepath}: {len(self.index)} trigrams in {time.perf_counter() - t0}s"
        )

    # except Exception as e:
    #     raise Exception(f"Failed to load search index from {filepath}: {e}")

    def search(self, query: str, limit: int) -> list[tuple[View[T], float]]:
        if not query:
            return []

        self.query = self._normalize_query(query)
        self.query_token_count = len(self.query.split())
        self.match_counts: dict[int, int] = defaultdict(int)
        self.trigram_count = 0

        self._build_match_counts()
        all_results: dict[int, tuple[View[T], float]] = {}
        scored_ids: set[int] = set()

        candidate_count = len(self.match_counts)

        if candidate_count <= self.CANDIDATE_CNT_THRESHOLD:
            for id in self.match_counts.keys():
                candidate = self.cache[id]
                score = self._score_candidate(candidate)
                if score >= self.NOISE_THRESHOLD:
                    all_results[id] = (candidate, score)
                scored_ids.add(id)
            return sorted(all_results.values(), key=lambda x: x[1], reverse=True)[
                :limit
            ]

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
        """Builds a mapping of document IDs to the count of matching trigrams with the query."""
        index = self.index
        match_counts = self.match_counts

        # If the index is small, consider all entries as matches
        if len(self.cache) < 300:
            for doc_id in self.cache.keys():
                match_counts[doc_id] = 1
            self.trigram_count = 1
            return

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

    def _get_search_values(self, candidate: View[T]):
        for field_name, weight in self.SEARCH_FIELDS.items():
            obj = candidate
            value = None
            for nested in field_name.split("."):
                value = getattr(obj, nested, None)
                if value is None:
                    break
                obj = value
            if value is not None:
                yield (value, weight)

    def _score_candidate(self, candidate: View[T]) -> float:
        score = 0.0
        total_weight = 0.0

        score_values = self._get_search_values(candidate)

        name, weight = next(score_values)  # name is always the first SEARCH_FIELD
        name_score = fuzz.WRatio(self.query, self._normalize_query(name)) / 100.0
        if name_score >= self.NOISE_THRESHOLD:
            score += name_score * weight
            total_weight += weight
        else:
            return 0.0

        if self.query_token_count > 1:
            for field_value, weight in score_values:
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
                        max(score for _, score, _ in matches) / 100.0
                        if matches
                        else 0.0
                    )
                else:
                    field_score = (
                        fuzz.token_set_ratio(self.query, normalize(field_value)) / 100.0
                    )

                if field_score >= self.NOISE_THRESHOLD:
                    score += field_score * weight
                    total_weight += weight

        return score / total_weight if total_weight > 0 else 0.0

    REMOVE_CHARS = (",", ".")

    def _normalize_query(self, text: str) -> str:
        norm = normalize(text)

        trans_table = str.maketrans("", "", "".join(self.REMOVE_CHARS))
        return norm.translate(trans_table)
