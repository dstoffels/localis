import pytest
from villager import countries, Country


class TestCountryGet:
    def test_country_get(self):
        for c in countries:
            country = countries.get(c.alpha2)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha2 == country.alpha2

    def test_country_get_by_alpha3(self):
        for c in countries:
            country = countries.get(c.alpha3)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha3 == country.alpha3

    def test_country_get_by_numeric(self):
        for c in countries:
            country = countries.get(c.numeric)
            assert isinstance(country, Country)
            assert country is not None
            assert c.numeric == country.numeric

    def test_country_get_with_alias(self):
        for alias, alpha_2 in countries.CODE_ALIASES.items():
            country = countries.get(alias)
            assert isinstance(country, Country)
            assert country is not None
            assert country.alpha2 == alpha_2

    def test_country_get_is_normalized(self):
        for c in countries:
            test = f"   {'.'.join(c.alpha2.split()).lower()}   "
            country = countries.get(test)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha2 == country.alpha2

    def test_country_get_none(self):
        country = countries.get("ZZZ")
        assert country is None


class TestCountryLookup:
    def test_country_lookup(self):
        for c in countries:
            results = countries.lookup(c.name)
            assert results
            assert len(results) > 0
            country = results[0]
            assert country.name == c.name

    def test_country_lookup_dupes(self):
        results = countries.lookup("Congo")
        alpha2s = [result.alpha2 for result in results]
        assert len(results) == 2
        assert "CG" in alpha2s
        assert "CD" in alpha2s

    def test_country_lookup_alias(self):
        for alias, name in countries.ALIASES.items():
            results = countries.lookup(alias)
            assert results
            assert len(results) > 0
            country = results[0]
            assert country.name == name

    def test_country_lookup_is_normalized(self):
        for c in countries:
            results = countries.lookup(f"   {c.name.lower()}   ")
            assert results
            assert len(results) > 0
            country = results[0]
            assert country.name == c.name

    def test_country_lookup_empty(self):
        results = countries.lookup("california")
        assert results == []


class TestCountrySearchAccuracy:
    def test_exact_name_should_rank_first(self):
        for c in countries:
            results = countries.search(c.name)
            assert results
            country, score = results[0]
            assert country.name == c.name
            assert score == 100


#     def test_alpha2_should_rank_first(self):
#         results = countries.search("FR")
#         assert results
#         country, score = results[0]
#         assert country.alpha2 == "FR"
#         assert score == 100

#     def test_alpha3_should_rank_first(self):
#         results = countries.search("DEU")
#         assert results
#         country, score = results[0]
#         assert country.alpha2 == "DE"
#         assert score == 100

#     def test_partial_name_with_multiple_candidates(self):
#         results = countries.search("Korea")
#         names = [c.name for c, _ in results]
#         assert "South Korea" in names
#         assert "North Korea" in names
#         # South should usually score higher?
#         assert results[0][0].name == "South Korea"

#     def test_fuzzy_match_high_score(self):
#         results = countries.search("Brasil")
#         assert results
#         top = results[0][0]
#         assert top.alpha2 == "BR"
#         assert top.name == "Brazil"

#     def test_common_misspelling(self):
#         results = countries.search("Argentinia")
#         assert results
#         top = results[0][0]
#         assert top.alpha2 == "AR"
#         assert top.name == "Argentina"

#     def test_country_search_wild_misspelling_united_states(self):
#         results = countries.search("yoonited staits of amrika")
#         names = [c.name for c, _ in results]
#         assert any("United States" in name for name in names)
#         assert len(results) > 0
