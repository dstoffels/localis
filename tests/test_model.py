import pytest
from villager.data.models import CountryModel, SubdivisionModel, CityModel, Model
from typing import Type
import villager
import random


def trunc(text: str) -> str:
    return text[:-2] if len(text) > 4 else text


def match_exact(model_cls: Type[Model], model: Model):
    results = model_cls.fts_match(model.name, limit=None)
    did_pass = any(model.name in r.name for r in results)
    if not did_pass:
        print(model.name, results)
    assert did_pass


class TestGet:
    """GET"""

    def test_returns_one(self):
        """should return a single, exact match"""
        result = CountryModel.get(CountryModel.alpha2 == "US")
        assert not isinstance(result, list)
        assert result.alpha2 == "US"

    def test_returns_none(self):
        """should return None if no match found"""
        result = CountryModel.get(CountryModel.name == "Chicago")
        assert result is None


class TestSelect:
    """SELECT"""

    def test_all(self):
        """should return entire table if no args given"""

        results = CountryModel.select()
        count = CountryModel.count()

        assert len(results) == count

    def test_list(self):
        """returns a list where every item matches exactly"""

        test = "United States|US|USA"
        results = SubdivisionModel.select(SubdivisionModel.country == test)
        assert all(test == s.country for s in results)


class TestFTSMatch:
    """FTS_MATCH"""

    sample = random.sample(list(villager.countries), 3)

    def test_limit(self):
        """should respect limits"""
        results = CountryModel.fts_match("US", limit=1)
        assert len(results) == 1

    def test_order_by(self):
        """should order the results"""
        results = CityModel.fts_match("madison", order_by=["population"])
        assert all(a.population <= b.population for a, b in zip(results, results[1:]))

    def test_columns(self):
        """should filter results by multiple columns"""
        field_queries = {"name": "Madison", "country": "US"}
        results = CityModel.fts_match(field_queries=field_queries)
        assert all("Madison" in r.name for r in results)
        assert all("US" in r.country for r in results)

    def test_bypass(self):
        """should bypass query arg when passing column-filtered queries"""
        query = "Bolivia"
        field_queries = {"name": "Bulgaria"}
        results = CountryModel.fts_match(query, field_queries)
        assert query not in [r.name for r in results]

    def test_falsy_query(self):
        """should return an empty list from falsy input"""
        results = CountryModel.fts_match(None)
        assert results == []

        results = CountryModel.fts_match("")
        assert results == []

    @pytest.mark.parametrize("country", sample, ids=lambda c: c.name)
    def test_exact(self, country: CountryModel):
        """should return a list of exact matches"""
        results = CountryModel.fts_match(country.name)
        assert country.name in [c.name for c in results]

    @pytest.mark.parametrize("country", sample, ids=lambda c: c.name)
    def test_prefix(self, country: CountryModel):
        """should return a matched list from truncated prefix"""
        results = CountryModel.fts_match(trunc(country.name), exact_match=False)
        assert country.name in [c.name for c in results]
