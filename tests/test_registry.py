import pytest
from villager import countries, subdivisions, cities
from villager.registries import Registry


REGISTRIES = [countries, subdivisions, cities]


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestGet:
    """GET"""

    def test_get_none(self, registry: Registry):
        """get should return none if no match found"""
        result = registry.get(id=-1)
        assert result is None


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestFilter:
    """FILTER"""

    def test_filter_none(self, registry: Registry):
        """should return an empty list when no matches found"""
        results = registry.filter("asjh238gjs")
        assert results == []

    def test_filter_limit(self, registry: Registry):
        """should limit the number of results"""
        results = registry.filter("us", limit=1)
        assert len(results) == 1

    def test_filter_query(self, registry: Registry):
        """should return a list of objects where any field contains the input"""
        query = "United"
        results = registry.filter(query)
        assert len(results) > 0
        assert all(
            any(query.lower() in str(value).lower() for value in vars(result).values())
            for result in results
        )

    def test_filter_by_name(self, registry: Registry):
        """should return a list of objects where the name field contains the name kwarg"""
        name = "Andorra"
        results = registry.filter(name=name)
        assert len(results) > 0, "should have at least 1 result"
        assert all(name in r.name for r in results)
