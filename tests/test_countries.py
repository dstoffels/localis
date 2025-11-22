from localis import countries, Country
import pytest


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

    def test_filter_by_official_name(self):
        """should filter results by country's official_name field"""

        country = countries.get(id=1)  # Andorra
        results = countries.filter(official_name=country.official_name)

        assert len(results) > 0, "should have more than 1 result"
        assert country in results

    def test_filter_by_alt_name(self, country: Country, select_random):
        """should filter results by country's alt_names field"""

        i = 1
        while not country.alt_names:
            country = select_random(countries, i)
            i += 1

        alt_name = country.alt_names[0]
        results = countries.filter(alt_name=alt_name)

        assert len(results) > 0, "should have at least 1 result"
        assert all(alt_name in r.alt_names for r in results)
