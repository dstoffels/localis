import pytest
import localis
from localis.registries import Registry
from localis.entities import Entity
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

    def test_limit(self, registry: Registry, select_random, include_historic):
        """should limit the number of results"""

        subject: Entity = select_random(registry)

        results = registry.filter(name=subject.name, limit=1)
        assert len(results) == 1

    def test_by_name(self, registry: Registry, select_random, include_historic):
        """should return a list of objects where the name field contains the name kwarg"""
        subject: Entity = select_random(registry)
        results: list[Entity] = registry.filter(name=subject.name)
        assert len(results) > 0, "should have at least 1 result"
        assert any(
            subject.name in [r.name] for r in results
        ), f"subject ({subject.name}) should be in results: {results}"


@pytest.mark.parametrize("level", [0, 1, 2, 3])
def test_subdivisions_by_int_admin_level(level: int):
    """an integer admin_level returns every subdivision at that level, since filter index cells are stored as strings"""
    results = localis.subdivisions.filter(admin_level=level)
    expected = {s.id for s in localis.subdivisions if s.admin_level == level}
    assert expected, f"the dataset should have subdivisions at admin_level={level}"
    assert {s.id for s in results} == expected
