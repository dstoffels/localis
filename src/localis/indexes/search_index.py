from array import array
from bisect import bisect_left
import heapq
import csv
import gzip
from pathlib import Path
from typing import Generic, Mapping, TypeVar
from localis.utils.data import IndexFilterPredicate
from rapidfuzz import fuzz
from localis.indexes.index import Index
from localis.entities import Entity
from localis.views import View
from localis.stores import Store
from localis.utils.strings import search_text, search_trigrams
from collections import Counter

T = TypeVar("T", bound=Entity)


class SearchIndex(Index, Generic[T]):
    def __init__(
        self,
        cache: Mapping[int, View[T, Store]],
        filepath: Path,
        **kwargs,
    ):
        self.cache = cache
        self.NOISE_THRESHOLD = 0.5
        # the share of a record's name score lost when none of the query outside its name fits its context
        self.CONTEXT_PENALTY = 0.5
        # how many of the best trigram matches go on to fuzzy scoring
        self.TOP_K = 50
        super().__init__(filepath, **kwargs)

    def load(
        self,
        data_path: Path,
        name_fields: tuple[str, ...],
        predicate: IndexFilterPredicate | None = None,
        allowed_ids: set[int] | None = None,
    ):
        self.NAME_FIELDS = name_fields
        self.canon, self.canon_counts = self._load_trigram_index(
            data_path / "canon_index", predicate, allowed_ids or set()
        )
        self.context, self.context_counts = self._load_trigram_index(
            data_path / "context_index", predicate, allowed_ids or set()
        )

    @staticmethod
    def _load_trigram_index(
        prefix: Path, predicate: IndexFilterPredicate | None, ids_allowed: set[int]
    ) -> tuple[dict[str, array], array]:
        """One trigram index's posting lists by trigram and its trigram count per record (position id - 1); a missing index is empty."""
        index: dict[str, array] = {}
        counts = array("H")
        blob_path = prefix.with_name(prefix.name + ".bin.gz")
        if not blob_path.exists():
            return index, counts

        offsets: dict[str, tuple[int, int]] = {}
        with open(
            prefix.with_name(prefix.name + "_offsets.tsv"), "r", encoding="utf-8"
        ) as f:
            reader = csv.reader(f, delimiter="\t")
            for trigram, offset, count in reader:
                offsets[trigram] = (int(offset), int(count))

        with gzip.open(blob_path, "rb") as f:
            full_array = array("I")
            full_array.frombytes(f.read())

        for trigram, (offset, count) in offsets.items():
            trigram_ids = full_array[offset : offset + count]
            if predicate:
                trigram_ids = array(
                    "I", (id for id in trigram_ids if predicate(id, ids_allowed))
                )
            index[trigram] = trigram_ids

        with gzip.open(prefix.with_name(prefix.name + "_counts.bin.gz"), "rb") as f:
            counts.frombytes(f.read())
        return index, counts

    def search(self, query: str, limit: int) -> list[tuple[View[T, Store], float]]:
        self.query = search_text(query)
        if not self.query:
            return []

        tokens = self.query.split()
        token_trigrams = [search_trigrams(token) for token in tokens]
        query_trigrams = set().union(*token_trigrams)
        canon_hits, context_hits = self._count_hits(query_trigrams)
        query_size = len(query_trigrams)

        def trigram_score(id: int) -> float:
            # the mean of how much of the query the record's names cover, and how much its names and context cover together
            canon = canon_hits[id]
            return (min(canon + context_hits[id], query_size) + canon) / (
                2 * query_size
            )

        # only records whose names share a trigram with the query qualify, so context alone (a city's state) never surfaces a record
        candidates = heapq.nlargest(
            max(self.TOP_K, limit), canon_hits, key=trigram_score
        )

        results: list[tuple[View[T, Store], float, float]] = []
        for id in candidates:
            candidate = self.cache[id]
            score = self._score_candidate(id, candidate, tokens, token_trigrams)
            if score >= self.NOISE_THRESHOLD:
                results.append((candidate, score, trigram_score(id)))

        # the candidate score ranks, the trigram score breaks its ties
        results.sort(key=lambda r: (r[1], r[2]), reverse=True)
        return [(candidate, score) for candidate, score, _ in results[:limit]]

    def _count_hits(
        self, query_trigrams: set[str]
    ) -> tuple[Counter[int], Counter[int]]:
        """Each record's count of the query's trigrams in its canon and in its context; Counter.update() counts an id array in C."""
        canon_hits: Counter[int] = Counter()
        context_hits: Counter[int] = Counter()
        for trigram in query_trigrams:
            if (ids := self.canon.get(trigram)) is not None:
                canon_hits.update(ids)
            if (ids := self.context.get(trigram)) is not None:
                context_hits.update(ids)
        return canon_hits, context_hits

    def _names(self, candidate: View[T, Store]) -> list[str]:
        """The search_text() of every value in the candidate's NAME_FIELDS, list fields such as aliases flattened."""
        names: list[str] = []
        for field_name in self.NAME_FIELDS:
            value = candidate
            for nested in field_name.split("."):
                value = getattr(value, nested, None)
                if value is None:
                    break
            for name in value if isinstance(value, (list, tuple)) else (value,):
                if isinstance(name, str) and (text := search_text(name)):
                    names.append(text)
        return names

    def _in_context(self, trigram: str, id: int) -> bool:
        ids = self.context.get(trigram)
        if ids is None:
            return False
        # posting lists are sorted by id
        i = bisect_left(ids, id)
        return i < len(ids) and ids[i] == id

    def _score_candidate(
        self,
        id: int,
        candidate: View[T, Store],
        tokens: list[str],
        token_trigrams: list[set[str]],
    ) -> float:
        """The candidate's best name match against any span of the query, reduced by the share of the rest of the query its context doesn't explain."""

        # the name span: for each name, slide a window of its word count over the query, so the name is found wherever it sits ("springfield illinois", "illinois springfield")
        name_score, span = 0.0, (0, len(tokens))
        for name in self._names(candidate):
            size = min(len(name.split()), len(tokens))
            for start in range(len(tokens) - size + 1):
                score = (
                    fuzz.token_sort_ratio(" ".join(tokens[start : start + size]), name)
                    / 100.0
                )
                if score > name_score:
                    name_score, span = score, (start, start + size)
        if name_score < self.NOISE_THRESHOLD:
            return 0.0

        # the rest of the query should locate the record: the share of its trigrams found in the record's context
        rest = set().union(*token_trigrams[: span[0]], *token_trigrams[span[1] :])
        if not rest:
            return name_score
        explained = sum(1 for trigram in rest if self._in_context(trigram, id)) / len(
            rest
        )
        return name_score * (1 - self.CONTEXT_PENALTY * (1 - explained))
