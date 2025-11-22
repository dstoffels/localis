import pytest
from localis import countries, subdivisions, cities
from localis.registries import Registry
from localis.dtos import DTO
from utils import mangle


REGISTRIES = [countries, subdivisions, cities]

# used to test all above registries with a single test
registry_param = pytest.mark.parametrize(
    "registry", REGISTRIES, ids=lambda r: type(r).__name__
)


@registry_param
class TestGet:
    """GET"""

    def test_none(self, registry: Registry):
        """should return None if no match found"""
        result = registry.get(id=-1)
        assert result is None

    def test_kwargs(self, registry: Registry):
        """should return None if given an invalid kwarg"""
        result = registry.get(pid=1)
        assert result is None


@registry_param
class TestFilter:
    """FILTER"""

    def test_none(self, registry: Registry):
        """should return [] if no matches are found"""
        results = registry.filter("asjh238gjs")
        assert results == []

    def test_kwargs(self, registry: Registry):
        """should return [] if given an invalid kwarg"""
        results = registry.filter(pid="1234")
        assert results == []

    def test_limit(self, registry: Registry):
        """should limit the number of results"""
        results = registry.filter("be", limit=1)
        assert len(results) == 1

    def test_query(self, registry: Registry):
        """should return a list of objects where at least one field contains the input query"""
        query = "Andorra"
        results: list[DTO] = registry.filter(query)
        assert len(results) > 0
        assert all(
            any(query.lower() in str(value).lower() for value in r.to_dict().values())
            for r in results
        ), "All results should have at least one field containing the query"

    def test_by_name(self, registry: Registry):
        """should return a list of objects where the name field contains the name kwarg"""
        name = "Andorra"
        results: list[DTO] = registry.filter(name=name)
        assert len(results) > 0, "should have at least 1 result"
        assert all(name in r.name for r in results)


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

    def test_exact(self, registry: Registry, select_random):
        """should return results containing the input subject."""

        subject = select_random(registry)
        results = registry.search(subject.name)

        assert subject in [r for r, _ in results]

    def test_mangled_name(self, registry: Registry, select_random, seed):
        """should return results with a top score >= 60% (minimum return threshold)"""
        subject: DTO = select_random(registry)
        mangled_name = mangle(subject.name, seed=seed)
        results = registry.search(mangled_name)
        _, top_score = results[0]

        assert (
            len(results) > 0
        ), f"Search returned no results for '{mangled_name}' (seed={seed})"
        assert (
            top_score >= 0.6
        ), f"should see a top score over 0.6. Top score: {top_score}"
