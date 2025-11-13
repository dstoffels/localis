from villager import countries, Country
import pytest
import random


def random_country() -> Country:
    id = random.choice(range(1, countries.count))
    return countries.get(id=id)


@pytest.fixture
def country() -> Country:
    return random_country()


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "alpha2", "alpha3", "numeric"])
    def test_get(self, field: str, country: Country):
        """should fetch a country by"""
        kwarg = {field: getattr(country, field)}
        result = countries.get(**kwarg)
        assert isinstance(result, Country)
        assert getattr(result, field) == getattr(country, field)


class TestFilter:
    """FILTER"""

    def test_filter_by_official_name(self, country: Country):
        """should filter results by country's official_name field"""
        while not country.official_name:
            country = random_country()

        results = countries.filter(official_name=country.official_name)

        assert len(results) > 0, "should have more than 1 result"
        assert all(country.official_name in r.official_name for r in results)

    def test_filter_by_alt_name(self, country: Country):
        """should filter results by country's alt_names field"""
        while not country.alt_names:
            country = random_country()

        alt_name = country.alt_names[0]
        results = countries.filter(alt_name=alt_name)

        assert len(results) > 0, "should have more than 1 result"
        assert all(alt_name in r.alt_names for r in results)
