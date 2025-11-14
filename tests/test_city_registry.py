import pytest
from villager import cities, City
from utils import select_random


@pytest.fixture
def city() -> City:
    return select_random(cities)


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "geonames_id"])
    def test_get(self, field: str, city: City):
        """should fetch city by:"""
        value = getattr(city, field)
        kwarg = {field: value}
        result = cities.get(**kwarg)
        assert isinstance(result, City)
        assert getattr(result, field) == value


class TestFilter:
    """FILTER"""

    @pytest.mark.parametrize("field", ["admin1", "admin2", "country"])
    def test_fields(self, field: str, city: City):
        """should return a list of cities where the field kwarg is in:"""
        assert False, "UNIMPLEMENTED"

    def test_alt_names(self, city: City):
        """should return a list of cities where the alt names contain the alt_name kwarg"""
        assert False, "UNIMPLEMENTED"
