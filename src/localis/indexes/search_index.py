from array import array
from bisect import bisect_left
import heapq
import math
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
from localis.utils.strings import search_text, search_trigrams, SHORT_NAME_MAX
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
        # how many records with the most canon and context hits get their exact weighted coverage computed, from which the TOP_K are taken
        self.SHORTLIST_K = 200
        # a trigram in more than this share of records (and more than STOP_MIN_DF of them) isn't counted when selecting, provided MIN_COUNTED rarer ones remain
        self.STOP_SHARE = 0.02
        self.STOP_MIN_DF = 1000
        self.MIN_COUNTED = 3
        # a one-word query this short has too few trigrams to find a typo'd name by, so it's also edit-distance matched against the shipped short names within one character of its length
        self.SHORT_QUERY_LEN = SHORT_NAME_MAX - 1
        # how many of those closest names, per length, join the candidates, and the least ratio they need
        self.SHORT_MATCH_K = 20
        self.SHORT_MATCH_CUTOFF = 70
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
        self.short_names = self._load_short_names(data_path / "short_names.tsv.gz", predicate, allowed_ids or set())
        self.context, self.context_counts = self._load_trigram_index(
            data_path / "context_index", predicate, allowed_ids or set()
        )

    @staticmethod
    def _load_short_names(
        path: Path, predicate: IndexFilterPredicate | None, ids_allowed: set[int]
    ) -> dict[int, tuple[list[str], array]]:
        """The shipped short names and their record ids, by name length; empty for a registry that ships none."""
        by_length: dict[int, tuple[list[str], array]] = {}
        if not path.exists():
            return by_length
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                name, id_s = line.rstrip("\n").split("\t")
                id = int(id_s)
                if predicate and not predicate(id, ids_allowed):
                    continue
                names, ids = by_length.setdefault(len(name), ([], array("I")))
                names.append(name)
                ids.append(id)
        return by_length

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
        weights = self._weights(query_trigrams)
        total_weight = sum(weights.values())

        # stage 1: count canon and context hits together in C over the query's rarer trigrams, and shortlist the records with the most
        hits = self._count_hits(query_trigrams)
        shortlist = [id for id, _ in hits.most_common(self.SHORTLIST_K)]

        # stage 2: each shortlisted record's rarity-weighted coverage of the query, by its names alone and by its names and context together, averaged
        trigram_scores: dict[int, float] = {}
        for id in shortlist:
            canon = context = 0.0
            for trigram, weight in weights.items():
                if self._contains(self.canon, trigram, id):
                    canon += weight
                elif self._contains(self.context, trigram, id):
                    context += weight
            # only records whose names share a trigram with the query qualify, so context alone (a city's state) never surfaces a record
            if canon:
                trigram_scores[id] = (2 * canon + context) / (2 * total_weight)
        candidates = heapq.nlargest(max(self.TOP_K, limit), trigram_scores, key=trigram_scores.__getitem__)
        # a short typo'd name shares only common edge trigrams with its record, so its edit-distance matches skip the trigram stages
        if self.short_names and len(tokens) == 1 and len(tokens[0]) <= self.SHORT_QUERY_LEN:
            candidates = list(dict.fromkeys([*candidates, *self._short_matches(tokens[0])]))

        # stage 3: fuzzy-score the candidates' names, with their context checked against the rest of the query
        results: list[tuple[View[T, Store], float, float]] = []
        for id in candidates:
            candidate = self.cache[id]
            score = self._score_candidate(id, candidate, tokens, token_trigrams, weights)
            if score >= self.NOISE_THRESHOLD:
                results.append((candidate, score, trigram_scores.get(id, 0.0)))

        # the candidate score ranks, the trigram score breaks its ties
        results.sort(key=lambda r: (r[1], r[2]), reverse=True)
        return [(candidate, score) for candidate, score, _ in results[:limit]]

    def _weights(self, query_trigrams: set[str]) -> dict[str, float]:
        """Each query trigram's rarity, log(records / records containing it) across canon and context; uniform if none carries any."""
        records = len(self.cache)
        weights: dict[str, float] = {}
        for trigram in query_trigrams:
            df = len(self.canon.get(trigram, ())) + len(self.context.get(trigram, ()))
            # a trigram no record has can't tell records apart, and one in every record says nothing either
            if df:
                weights[trigram] = max(math.log(records / df), 0.0)
        if not any(weights.values()):
            return {trigram: 1.0 for trigram in query_trigrams}
        return {trigram: weight for trigram, weight in weights.items() if weight}

    def _count_hits(self, query_trigrams: set[str]) -> Counter[int]:
        """Each record's count of the query's trigrams in its canon and its context, leaving out the most common trigrams (in canon only when enough rarer ones remain); Counter.update() counts an id array in C."""
        # a trigram shared by a large share of records is the most expensive to count and says the least about which record matches, such as a country name's trigrams in the context of every city in it
        common = max(self.STOP_SHARE * len(self.cache), self.STOP_MIN_DF)
        canon = [ids for trigram in query_trigrams if (ids := self.canon.get(trigram)) is not None]
        rarer_canon = [ids for ids in canon if len(ids) <= common]
        rarer_context = [ids for trigram in query_trigrams if (ids := self.context.get(trigram)) is not None and len(ids) <= common]
        hits: Counter[int] = Counter()
        for ids in rarer_canon if len(rarer_canon) >= self.MIN_COUNTED else canon:
            hits.update(ids)
        for ids in rarer_context:
            hits.update(ids)
        return hits

    def _raw_names(self, candidate: View[T, Store]):
        """Every value in the candidate's NAME_FIELDS, list fields such as aliases flattened."""
        for field_name in self.NAME_FIELDS:
            value = candidate
            for nested in field_name.split("."):
                value = getattr(value, nested, None)
                if value is None:
                    break
            for name in value if isinstance(value, (list, tuple)) else (value,):
                if isinstance(name, str) and name:
                    yield name

    def _names(self, candidate: View[T, Store]) -> list[str]:
        """The search_text() of every name in the candidate's NAME_FIELDS."""
        return [text for name in self._raw_names(candidate) if (text := search_text(name))]

    def _short_matches(self, token: str) -> list[int]:
        """The records whose shipped short names, within one character of the token's length, are closest to it by ratio."""
        matches: list[int] = []
        for length in range(len(token) - 1, len(token) + 2):
            if (bucket := self.short_names.get(length)) is None:
                continue
            names, ids = bucket
            for _, _, i in process.extract(token, names, scorer=fuzz.ratio, limit=self.SHORT_MATCH_K, score_cutoff=self.SHORT_MATCH_CUTOFF):
                matches.append(ids[i])
        return matches

    @staticmethod
    def _contains(index: dict[str, array], trigram: str, id: int) -> bool:
        ids = index.get(trigram)
        if ids is None:
            return False
        # posting lists are sorted by id
        i = bisect_left(ids, id)
        return i < len(ids) and ids[i] == id

    def _explained(self, id: int, token_trigrams: list[set[str]], span: tuple[int, int], weights: dict[str, float]) -> float:
        """The rarity-weighted share of the query's trigrams outside the name span found in the record's context; 1.0 when nothing weighted is left outside it."""
        rest = set().union(*token_trigrams[: span[0]], *token_trigrams[span[1] :])
        rest_weight = sum(weights.get(trigram, 0.0) for trigram in rest)
        if not rest_weight:
            return 1.0
        return sum(weights.get(trigram, 0.0) for trigram in rest if self._contains(self.context, trigram, id)) / rest_weight

    def _score_candidate(self, id: int, candidate: View[T, Store], tokens: list[str], token_trigrams: list[set[str]], weights: dict[str, float]) -> float:
        """The best, over the candidate's names and the query spans each could fill, of the name match reduced by the share of the rest of the query its context doesn't explain."""
        best = 0.0
        explained: dict[tuple[int, int], float] = {}
        # for each name, slide a window of its word count over the query, so the name is found wherever it sits ("springfield illinois", "illinois springfield")
        for name in self._names(candidate):
            size = min(len(name.split()), len(tokens))
            for start in range(len(tokens) - size + 1):
                span_text = " ".join(tokens[start : start + size])
                name_score = fuzz.token_sort_ratio(span_text, name) / 100.0
                # a typo can change the sorted word order ("alto alxgre" vs "alegre alto"), which plain ratio, comparing words as typed, doesn't suffer; two single words can't be reordered, so they need no second call
                if size > 1 or " " in name:
                    name_score = max(name_score, fuzz.ratio(span_text, name) / 100.0)
                # the context factor never raises a score, so a span that can't beat the best on its name alone is skipped
                if name_score <= best:
                    continue
                span = (start, start + size)
                if span not in explained:
                    explained[span] = self._explained(id, token_trigrams, span, weights)
                best = max(best, name_score * (1 - self.CONTEXT_PENALTY * (1 - explained[span])))
        return best
