import pytest
from localis.registries import Registry
from localis.entities import Entity
from utils import registry_param, mangle


@registry_param
class TestSearch:
    """SEARCH"""

    @pytest.mark.parametrize("bad_q", ["", "zzzzzzzzz", "!@#$%"])
    def test_empty(self, bad_q, registry: Registry):
        """should return [] with bad or no input."""

        results = registry.search(bad_q)
        assert isinstance(results, list)
        assert (
            not results
        ), f"query: {bad_q} should yield [], instead returned {results}"

    def test_exact(self, registry: Registry, select_random, include_historic):
        """should return results containing the input subject."""

        subject: Entity = select_random(registry)
        results = registry.search(subject.name)

        assert subject.name in [
            r.name for r, _ in results
        ], f"should find exact match for '{subject.name}'"

    def test_mangled_name(self, registry: Registry, select_random, seed, include_historic):
        """should return results with a top score >= 50% (minimum return threshold)"""
        subject: Entity = select_random(registry)
        mangled_name = mangle(subject.name, seed=seed)
        results = registry.search(mangled_name)
        if results:
            _, top_score = results[0]

            assert (
                top_score >= 0.5
            ), f"should see a top score over 0.5. Top score: {top_score}"
