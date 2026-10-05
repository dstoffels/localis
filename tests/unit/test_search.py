from pathlib import Path
from typing import Any
import pytest
from ingest.shared.models import CurrencyModel
from ingest.utils import index
from localis.registries import QueryableRegistry
from localis.entities import Entity
from localis.indexes import SearchIndex
from localis.views import CurrencyView
from utils import queryable_registry_param, mangle


@queryable_registry_param
class TestSearch:
    """SEARCH"""

    @pytest.mark.parametrize("bad_q", ["", "zzzzzzzzz", "!@#$%"])
    def test_empty(self, bad_q, registry: QueryableRegistry):
        """should return [] with bad or no input."""

        results = registry.search(bad_q)
        assert isinstance(results, list)
        assert (
            not results
        ), f"query: {bad_q} should yield [], instead returned {results}"

    @pytest.mark.parametrize("bad_limit", [0, -1, True])
    def test_bad_limit(self, bad_limit, registry: QueryableRegistry):
        """should raise a ValueError for a limit that isn't a positive integer, rather than slice by it"""
        with pytest.raises(ValueError):
            registry.search("paris", limit=bad_limit)

    def test_kwargs(self, registry: QueryableRegistry):
        """should raise a TypeError if given an invalid kwarg"""
        kwargs: dict[str, Any] = {"pid": "1234"}
        with pytest.raises(TypeError):
            registry.search("paris", **kwargs)

    def test_exact(self, registry: QueryableRegistry, select_random, include_historic):
        """should return results containing the input subject."""

        subject: Entity = select_random(registry)
        results = registry.search(subject.name)

        assert subject.name in [
            r.name for r, _ in results
        ], f"should find exact match for '{subject.name}'"

    def test_result_shape(self, registry: QueryableRegistry, select_random, seed, include_historic):
        """should return at most limit distinct records, best first, each scored from the noise threshold to 1, for an exact and a mangled query"""
        subject: Entity = select_random(registry)
        limit = 5

        for query in (subject.name, mangle(subject.name, seed=seed)):
            results = registry.search(query, limit=limit)
            scores = [score for _, score in results]
            ids = [r.id for r, _ in results]

            assert len(results) <= limit, f"[{query}] returned {len(results)} results for limit {limit}"
            assert all(SearchIndex.NOISE_THRESHOLD <= score <= 1 for score in scores), f"[{query}] scored outside [{SearchIndex.NOISE_THRESHOLD}, 1]: {scores}"
            assert scores == sorted(scores, reverse=True), f"[{query}] scores aren't best first: {scores}"
            assert len(ids) == len(set(ids)), f"[{query}] returned a record twice: {ids}"


class TestSearchLimit:
    """SEARCH LIMIT"""

    def test_limit_beyond_shortlist(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """should return up to limit matches when limit is larger than the shortlist and the fuzzy-scored candidates"""
        monkeypatch.setattr(index, "STAGED_DATA_PATH", tmp_path)
        # a name too long for the short-query fallback, so only the trigram stages find the records
        index.dump_registry("currencies", [CurrencyModel(name="Demonstration", alpha3=f"D{c}{c}", numeric=None) for c in "ABCDE"])
        search_index = SearchIndex(CurrencyView.load(tmp_path / "currencies" / "currencies.tsv"), tmp_path / "currencies", ("name",))
        monkeypatch.setattr(search_index, "SHORTLIST_K", 1)
        monkeypatch.setattr(search_index, "TOP_K", 1)

        assert len(search_index.search("demonstration", limit=5)) == 5
