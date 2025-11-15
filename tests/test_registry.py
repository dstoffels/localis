import pytest
from villager import countries, subdivisions, cities
from villager.registries import Registry
from villager.dtos import DTO
from utils import select_random, mangle
import random

REGISTRIES = [countries, subdivisions, cities]


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
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


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
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


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestSearch:
    """SEARCH"""

    def test_empty(self, registry: Registry):
        """should return [] with bad or no input."""

        bad_queries = ["", "fh23897yuh"]
        for q in bad_queries:
            results = registry.search(q)
            assert isinstance(results, list)
            assert (
                not results
            ), f"query: {q} should yield [], instead returned {results}"

    def test_exact(self, registry: Registry):
        """should return a list of objects with at least one field matching input query"""

        subject = select_random(registry)
        results = registry.search(subject.name)

        assert any(subject.name == r.name for r, score in results)

    def test_mangled(self, registry: Registry):
        """should return a list of objects with at least one field matching input query"""
        COUNT = 50
        ids = random.choices(range(1, registry.count), k=COUNT + 1)
        test_subjects: list[DTO] = []
        for id in ids:
            test_subjects.append(registry.get(id=id))

        successes = 0
        for subj in test_subjects:
            results: list[tuple[DTO, float]] = registry.search(mangle(subj.name))
            if any(subj.id == r.id for r, score in results):
                successes += 1

        assert successes > 0
        rate = successes / COUNT
        assert rate > 0.5
