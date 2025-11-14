from villager import countries, Country
import pytest
from utils import select_random


@pytest.fixture
def country() -> Country:
    return select_random(countries)


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "alpha2", "alpha3", "numeric"])
    def test_get(self, field: str, country: Country):
        """should fetch a country by"""
        value = getattr(country, field)
        kwarg = {field: value}
        result = countries.get(**kwarg)
        assert isinstance(result, Country)
        assert getattr(result, field) == value


class TestFilter:
    """FILTER"""

    def test_filter_by_official_name(self, country: Country):
        """should filter results by country's official_name field"""
        while not country.official_name:
            country = select_random(countries)

        results = countries.filter(official_name=country.official_name)

        assert len(results) > 0, "should have more than 1 result"
        assert all(country.official_name in r.official_name for r in results)

    def test_filter_by_alt_name(self, country: Country):
        """should filter results by country's alt_names field"""
        while not country.alt_names:
            country = select_random(countries)

        alt_name = country.alt_names[0]
        results = countries.filter(alt_name=alt_name)

        assert len(results) > 0, "should have at least 1 result"
        assert all(alt_name in r.alt_names for r in results)
