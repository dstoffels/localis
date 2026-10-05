import pytest
from localis.registries import QueryableRegistry
from localis.entities import Entity
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
        with pytest.raises(TypeError):
            registry.search("paris", pid="1234")  # type: ignore[call-arg]

    def test_exact(self, registry: QueryableRegistry, select_random, include_historic):
        """should return results containing the input subject."""

        subject: Entity = select_random(registry)
        results = registry.search(subject.name)

        assert subject.name in [
            r.name for r, _ in results
        ], f"should find exact match for '{subject.name}'"

    def test_mangled_name(
        self, registry: QueryableRegistry, select_random, seed, include_historic
    ):
        """should return results with a top score >= 50% (minimum return threshold)"""
        subject: Entity = select_random(registry)
        mangled_name = mangle(subject.name, seed=seed)
        results = registry.search(mangled_name)
        if results:
            _, top_score = results[0]

            assert (
                top_score >= 0.5
            ), f"should see a top score over 0.5. Top score: {top_score}"
