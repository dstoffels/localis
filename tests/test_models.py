import pytest
from villager.db.models import CountryModel, SubdivisionModel, CityModel, Model
from typing import Type


def trunc(word: str) -> str:
    return word[:2] if len(word) > 4 else word


def match_exact(model_cls: Type[Model], model: Model):
    results = model_cls.fts_match(model.name, exact_match=True, limit=None)
    did_pass = any(model.name in r.name for r in results)
    if not did_pass:
        print(model.name, results)
    assert did_pass


class TestGet:
    """GET"""

    def test_returns_one(self):
        """returns an exact match from field"""
        result = CountryModel.get(CountryModel.alpha2 == "US")
        assert not isinstance(result, list)
        assert result.alpha2 == "US"

    def test_returns_none(self):
        """returns None if no match"""
        result = CountryModel.get(CountryModel.name == "Chicago")
        assert result is None


class TestSelect:
    """SELECT"""

    def test_all(self):
        """returns the entire table with no params"""

        results = CountryModel.select()
        count = CountryModel.count()

        assert len(results) == count

    def test_list(self):
        """returns a list where every item matches exactly"""

        test = "United States|US|USA"
        results = SubdivisionModel.select(SubdivisionModel.country == test)
        assert all(test == s.country for s in results)


class TestFTSMatch:
    """FTS Matching"""

    @pytest.fixture
    def countries(self):
        return CountryModel.select()

    @pytest.fixture
    def subdivisions(self):
        return SubdivisionModel.select()

    @pytest.fixture
    def cities(self):
        return CityModel.select()

    def test_limit(self):
        """respects limit"""
        results = CountryModel.fts_match("US", limit=1, exact_match=True)
        assert len(results) == 1

    def test_order_by(self):
        """sorts results"""
        results = CityModel.fts_match("madison", order_by=["population"])
        assert all(a.population <= b.population for a, b in zip(results, results[1:]))

    def test_falsy_query(self):
        """returns empty list with falsy input"""
        results = CountryModel.fts_match(None)
        assert results == []

        results = CountryModel.fts_match("")
        assert results == []

    def test_exact(self, countries: list[CountryModel], subdivisions, cities):
        """returns a list of exact matches"""

        for country in countries:
            results = CountryModel.fts_match(country.name, exact_match=True, limit=None)
            assert any(country.name in c.name for c in results)

        for sub in subdivisions:
            results = SubdivisionModel.fts_match(sub.name, exact_match=True, limit=None)
            assert any(sub.name in s.name for s in results)

        for city in cities[:50000]:
            results = CityModel.fts_match(city.name, exact_match=True, limit=None)
            passes = any(city.name in c.name for c in results)
            if not passes:
                print(city.name)
                print(results)
            assert passes

    def test_prefix(self, countries: list[CountryModel], subdivisions, cities):
        """returns a matched list from truncated prefix"""
        for country in countries:
            prefix = trunc(country.name)
            results = CountryModel.fts_match(prefix, limit=1000)
            assert any(country.name in c.name for c in results)

        for sub in subdivisions[:5000]:
            prefix = trunc(sub.name)
            results = SubdivisionModel.fts_match(prefix, limit=1000)
            assert any(sub.name in s.name for s in results)

        # skipping cities for this test due to huge dataset

        # for city in cities[:5000]:
        #     prefix = trunc(city.name)
        #     results = CityModel.fts_match(prefix, limit=1000)
        #     assert any(city.name in c.name for c in results)
