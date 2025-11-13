import pytest
from villager import countries, Country
from utils import mangle
import time


class TestGet:
    """GET"""

    @pytest.mark.parametrize(
        "attr", ["id", "alpha2", "alpha3", "numeric"], ids=lambda p: p
    )
    @pytest.mark.parametrize("country", countries, ids=lambda c: c.name)
    def test_inputs(self, country, attr):
        """should return match from identifiers"""
        val = getattr(country, attr)
        result = countries.get(**{attr: val})
        assert isinstance(result, Country)
        assert getattr(result, attr) == val

    def test_is_normalized(self):
        """should normalize input"""
        for c in countries:
            test = f"   {'.'.join(c.alpha2.split()).lower()}   "
            country = countries.get(alpha2=test)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha2 == country.alpha2

    def test_none(self):
        """should return none with bad input"""
        country = countries.get(alpha2="ZZZ")
        assert country is None


class TestLookup:
    """LOOKUP"""

    def test_lookup(self):
        """should return a list containing input country"""
        for c in countries:
            results = countries.filter(c.name)
            assert results
            assert any(c.id == r.id for r in results)

    def test_is_normalized(self):
        """should normalize input"""
        for c in countries:
            results = countries.filter(f"   {c.name.lower()}   ")
            assert results
            assert any(c.name == r.name for r in results)

    def test_none(self):
        """should return [] with bad input"""
        results = countries.filter("california")
        assert results == []

    def test_limit(self):
        """should respect limits"""
        limit = 1
        results = countries.filter("Congo", limit=limit)
        assert len(results) == limit


# class TestSearch:
#     def test_none(self):
#         results = countries.search("")
#         assert results == []

#     def test_exact_ranks_first(self):
#         for c in countries:
#             results = countries.search(c.name)
#             assert results
#             country = results[0]
#             assert (
#                 country.name == c.name
#             ), f"Expected result {country.name} to match {c.name}. {results}"

#             # results = countries.search(c.alpha2)
#             # assert results
#             # country = results[0]
#             # assert (
#             #     country.alpha2 == c.alpha2
#             # ), f"Expected result {country.alpha2} to match {c.alpha2}"

#             # results = countries.search(c.alpha3)
#             # assert results
#             # country, score = results[0]
#             # assert (
#             #     country.alpha3 == c.alpha3
#             # ), f"Expected result {country.alpha3} to match {c.alpha3}"

#     def test_typos_top1(self):
#         seeds = range(20)  # Test different seeds
#         success_count = 0
#         total = 0
#         typo_rate = 0.15
#         success_threshold = 0.85

#         for seed in seeds:
#             for c in countries:
#                 test = mangle(c.name, typo_rate, seed)
#                 results = countries.search(test)
#                 total += 1

#                 if not results:
#                     continue

#                 top_result = results[0]
#                 if top_result.name == c.name:
#                     success_count += 1

#         accuracy = success_count / total
#         print(f"\n{success_count} / {total} = {accuracy:.2%} accuracy")
#         assert (
#             accuracy >= success_threshold
#         ), f"{accuracy:.2%} accuracy below threshold {success_threshold:.2%}"


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
