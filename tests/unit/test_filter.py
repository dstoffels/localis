from localis.registries import Registry
from localis.models import DTO
from utils import registry_param


@registry_param
class TestFilter:
    """FILTER"""

    def test_none(self, registry: Registry):
        """should return [] if no matches are found"""
        results = registry.filter(name="asjh238gjs")
        assert results == []

    def test_kwargs(self, registry: Registry):
        """should return [] if given an invalid kwarg"""
        results = registry.filter(pid="1234")
        assert results == []

    def test_limit(self, registry: Registry, select_random):
        """should limit the number of results"""

        subject: DTO = select_random(registry)

        results = registry.filter(name=subject.name, limit=1)
        assert len(results) == 1

    def test_by_name(self, registry: Registry, select_random):
        """should return a list of objects where the name field contains the name kwarg"""
        subject: DTO = select_random(registry)
        results: list[DTO] = registry.filter(name=subject.name)
        assert len(results) > 0, "should have at least 1 result"
        assert all(subject.name in r.name for r in results)
