import pytest
from villager import countries, subdivisions, cities
from villager.registries import Registry
from villager.dtos import DTO


REGISTRIES = [countries, subdivisions, cities]


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestGet:
    """GET"""

    def test_get_none(self, registry: Registry):
        """should return None if no match found"""
        result = registry.get(id=-1)
        assert result is None

    def test_get_kwargs(self, registry: Registry):
        """should return None if given an invalid kwarg"""
        result = registry.get(pid=1)
        assert result is None


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestFilter:
    """FILTER"""

    def test_filter_none(self, registry: Registry):
        """should return [] if no matches are found"""
        results = registry.filter("asjh238gjs")
        assert results == []

    def test_filter_kwargs(self, registry: Registry):
        """should return [] if given an invalid kwarg"""
        results = registry.filter(pid="1234")
        assert results == []

    def test_filter_limit(self, registry: Registry):
        """should limit the number of results"""
        results = registry.filter("be", limit=1)
        assert len(results) == 1

    def test_filter_query(self, registry: Registry):
        """should return a list of objects where at least one field contains the input query"""
        query = "Andorra"
        results: list[DTO] = registry.filter(query)
        assert len(results) > 0
        assert all(
            any(query.lower() in str(value).lower() for value in r.to_dict().values())
            for r in results
        ), "All results should have at least one field containing the query"

    def test_filter_by_name(self, registry: Registry):
        """should return a list of objects where the name field contains the name kwarg"""
        name = "Andorra"
        results = registry.filter(name=name)
        assert len(results) > 0, "should have at least 1 result"
        assert all(name in r.name for r in results)
