from array import array
import csv
import gzip
from pathlib import Path
from typing import Generic, Mapping, TypeVar
from localis.utils.data import IndexFilterPredicate
from rapidfuzz import fuzz, process
from localis.indexes.index import Index
from localis.entities import Entity
from localis.views import View
from localis.stores import Store
from localis.utils.strings import search_text, search_trigrams
from collections import defaultdict

T = TypeVar("T", bound=Entity)


class SearchIndex(Index, Generic[T]):
    def __init__(
        self,
        cache: Mapping[int, View[T, Store]],
        filepath: Path,
        **kwargs,
    ):
        self.cache = cache
        self.PRIMARY_WEIGHT = 1.0
        self.NOISE_THRESHOLD = 0.5
        self.STRONG_MATCH_THRESHOLD = 0.8
        self.CANDIDATE_CNT_THRESHOLD = 2000
        super().__init__(filepath, **kwargs)

    def load(
        self,
        filepath: Path,
        offsets_filepath: Path,
        fields_filepath: Path,
        predicate: IndexFilterPredicate | None = None,
        allowed_ids: set[int] | None = None,
    ):
        ids_allowed = allowed_ids or set()
        self.index: dict[str, array] = {}
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
            trigram_ids = full_array[offset : offset + count]
            if predicate:
                trigram_ids = array(
                    "I", (id for id in trigram_ids if predicate(id, ids_allowed))
                )
            self.index[trigram] = trigram_ids

    def search(self, query: str, limit: int) -> list[tuple[View[T, Store], float]]:
        self.query = search_text(query)
        if not self.query:
            return []

        self.query_token_count = len(self.query.split())
        self.match_counts: dict[int, int] = defaultdict(int)
        self.trigram_count = 0

        self._build_match_counts()
        all_results: dict[int, tuple[View[T, Store], float]] = {}
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

        for trigram in search_trigrams(self.query):
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

    def _get_search_values(self, candidate: View[T, Store]):
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

    def _score_candidate(self, candidate: View[T, Store]) -> float:
        score_values = list(self._get_search_values(candidate))

        # the primary score is the best of the single-valued, full-weight name fields (a country's ISO name, official name and common name), so a candidate matching by any of its names passes the noise gate
        primary = [
            (v, w)
            for v, w in score_values
            if w >= self.PRIMARY_WEIGHT and isinstance(v, str)
        ]
        name_score, weight = max(
            (fuzz.WRatio(self.query, search_text(v)) / 100.0, w) for v, w in primary
        )
        if name_score < self.NOISE_THRESHOLD:
            return 0.0
        score = name_score * weight
        total_weight = weight

        if self.query_token_count > 1:
            for field_value, weight in score_values:
                if not field_value or (
                    weight >= self.PRIMARY_WEIGHT and isinstance(field_value, str)
                ):
                    continue

                if isinstance(field_value, (list, tuple)):
                    matches = process.extract(
                        self.query,
                        [search_text(v) for v in field_value],
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
                        fuzz.token_set_ratio(self.query, search_text(field_value))
                        / 100.0
                    )

                if field_score >= self.NOISE_THRESHOLD:
                    score += field_score * weight
                    total_weight += weight

        # secondary fields corroborate a match but never weaken it, so an exact name match isn't averaged down by its aliases
        return max(name_score, score / total_weight)
