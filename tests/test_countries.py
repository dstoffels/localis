import pytest
from typing import Optional
from villager import countries, Country


class TestCountryGet:
    def test_country_get_us(self):
        country = countries.get("US")
        assert isinstance(country, Country | None)
        assert country is not None
        assert country.name == "United States"

    def test_country_get_by_alpha3(self):
        country = countries.get("USA")
        assert isinstance(country, Country | None)
        assert country is not None
        assert country.alpha2 == "US"

    def test_country_get_by_numeric(self):
        country = countries.get(840)
        assert isinstance(country, Country | None)
        assert country is not None
        assert country.alpha2 == "US"

    def test_country_get_with_alias(self):
        country = countries.get("UK")
        assert isinstance(country, Country | None)
        assert country is not None
        assert country.alpha2 == "GB"

    def test_country_get_none(self):
        country = countries.get("ZZZ")
        assert country is None


class TestCountryLookup:
    def test_country_lookup_us(self):
        country = countries.lookup("United States")[0]
        assert isinstance(country, Country | None)
        assert country is not None
        assert country.alpha2 == "US"


class TestCountrySearchAccuracy:
    def test_exact_name_should_rank_first(self):
        results = countries.search("Georgia")
        assert results
        country, score = results[0]
        assert country.name == "Georgia"
        assert country.alpha2 == "GE"
        assert score == 100

    def test_alpha2_should_rank_first(self):
        results = countries.search("FR")
        assert results
        country, score = results[0]
        assert country.alpha2 == "FR"
        assert score == 100

    def test_alpha3_should_rank_first(self):
        results = countries.search("DEU")
        assert results
        country, score = results[0]
        assert country.alpha2 == "DE"
        assert score == 100

    def test_partial_name_with_multiple_candidates(self):
        results = countries.search("Korea")
        names = [c.name for c, _ in results]
        assert "South Korea" in names
        assert "North Korea" in names
        # South should usually score higher?
        assert results[0][0].name == "South Korea"

    def test_fuzzy_match_high_score(self):
        results = countries.search("Brasil")
        assert results
        top = results[0][0]
        assert top.alpha2 == "BR"
        assert top.name == "Brazil"

    def test_common_misspelling(self):
        results = countries.search("Argentinia")
        assert results
        top = results[0][0]
        assert top.alpha2 == "AR"
        assert top.name == "Argentina"

    def test_country_search_wild_misspelling_united_states(self):
        results = countries.search("yoonited staits of amrika")
        names = [c.name for c, _ in results]
        assert any("United States" in name for name in names)
        assert len(results) > 0
