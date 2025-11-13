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
