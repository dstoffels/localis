# import pytest
# from villager import countries, Country
# from utils import mangle
# import time


# @pytest.fixture(autouse=True)
# def track_test_metrics(request):
#     start = time.perf_counter()
#     yield
#     duration = time.perf_counter() - start
#     print(f"\nTest {request.node.name} took {duration:.3f}s")


# class TestGet:
#     def test_alpha2(self):
#         for c in countries:
#             country = countries.get(c.alpha2)
#             assert isinstance(country, Country)
#             assert country is not None
#             assert c.alpha2 == country.alpha2

#     def test_alpha3(self):
#         for c in countries:
#             country = countries.get(c.alpha3)
#             assert isinstance(country, Country)
#             assert country is not None
#             assert c.alpha3 == country.alpha3

#     def test_numeric(self):
#         for c in countries:
#             country = countries.get(c.numeric)
#             assert isinstance(country, Country)
#             assert country is not None
#             assert c.numeric == country.numeric

#     def test_aliases(self):
#         for alias, alpha_2 in countries.CODE_ALIASES.items():
#             country = countries.get(alias)
#             assert isinstance(country, Country)
#             assert country is not None
#             assert country.alpha2 == alpha_2

#     def test_is_normalized(self):
#         for c in countries:
#             test = f"   {'.'.join(c.alpha2.split()).lower()}   "
#             country = countries.get(test)
#             assert isinstance(country, Country)
#             assert country is not None
#             assert c.alpha2 == country.alpha2

#     def test_none(self):
#         country = countries.get("ZZZ")
#         assert country is None


# class TestLookup:
#     def test_lookup(self):
#         for c in countries:
#             results = countries.lookup(c.name)
#             assert results
#             assert len(results) > 0
#             country = results[0]
#             assert country.name == c.name

#     def test_dupes(self):
#         results = countries.lookup("Congo")
#         alpha2s = [result.alpha2 for result in results]
#         assert len(results) == 2
#         assert "CG" in alpha2s
#         assert "CD" in alpha2s

#     def test_aliases(self):
#         for alias, name in countries.ALIASES.items():
#             results = countries.lookup(alias)
#             assert results
#             assert len(results) > 0
#             country = results[0]
#             assert country.name == name

#     def test_is_normalized(self):
#         for c in countries:
#             results = countries.lookup(f"   {c.name.lower()}   ")
#             assert results
#             assert len(results) > 0
#             country = results[0]
#             assert country.name == c.name

#     def test_none(self):
#         results = countries.lookup("california")
#         assert results == []


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


# #     def test_partial_name_with_multiple_candidates(self):
# #         results = countries.search("Korea")
# #         names = [c.name for c, _ in results]
# #         assert "South Korea" in names
# #         assert "North Korea" in names
# #         # South should usually score higher?
# #         assert results[0][0].name == "South Korea"

# #     def test_fuzzy_match_high_score(self):
# #         results = countries.search("Brasil")
# #         assert results
# #         top = results[0][0]
# #         assert top.alpha2 == "BR"
# #         assert top.name == "Brazil"

# #     def test_common_misspelling(self):
# #         results = countries.search("Argentinia")
# #         assert results
# #         top = results[0][0]
# #         assert top.alpha2 == "AR"
# #         assert top.name == "Argentina"

# #     def test_country_search_wild_misspelling_united_states(self):
# #         results = countries.search("yoonited staits of amrika")
# #         names = [c.name for c, _ in results]
# #         assert any("United States" in name for name in names)
# #         assert len(results) > 0
