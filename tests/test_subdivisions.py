# import pytest
# from villager import subdivisions
# from villager.types import Subdivision


# class TestSubdivisionByCountry:
#     def test_by_country_alpha2(self):
#         results: list[Subdivision] = subdivisions.by_country("US")
#         assert results
#         assert all(sub.country_alpha2 == "US" for sub in results)

#     def test_by_country_alpha3(self):
#         results: list[Subdivision] = subdivisions.by_country("USA")
#         assert results
#         assert all(sub.country_alpha2 == "US" for sub in results)

#     def test_by_country_name(self):
#         results: list[Subdivision] = subdivisions.by_country("United States")
#         assert results
#         assert all(sub.country_alpha2 == "US" for sub in results)

#     def test_by_country_case_insensitive(self):
#         results: list[Subdivision] = subdivisions.by_country("united states")
#         assert results
#         assert all(sub.country_alpha2 == "US" for sub in results)

#     def test_by_country_alias(self):
#         results = subdivisions.by_country("UK")
#         assert results
#         assert all(sub.country_code == "GB" for sub in results)

#     def test_by_country_invalid(self):
#         results: list[Subdivision] = subdivisions.by_country("ZZ")
#         assert results == []

#     def test_by_country_empty(self):
#         results: list[Subdivision] = subdivisions.by_country("")
#         assert results == []


# class TestSubdivisionlookupTypes:
#     def test_lookup_types_alpha2(self):
#         types = subdivisions.lookup_types("US")
#         assert types
#         assert isinstance(types, list)
#         assert "state" in types

#     def test_lookup_types_alpha3(self):
#         types = subdivisions.lookup_types("USA")
#         assert types
#         assert isinstance(types, list)

#     def test_lookup_types_name(self):
#         types = subdivisions.lookup_types("United States")
#         assert types
#         assert isinstance(types, list)
#         assert "state" in types or "territory" in types

#     def test_lookup_types_uk_alias(self):
#         types = subdivisions.lookup_types("UK")
#         assert types
#         assert isinstance(types, list)
#         assert "country" in types

#     def test_lookup_types_case_insensitivity():
#         inputs = ["us", "USA", "uSa", "UnIteD STaTEs", "united states"]
#         expected_types = subdivisions.lookup_types("US")

#         for inp in inputs:
#             types = subdivisions.lookup_types(inp)
#             assert types == expected_types

#     def test_lookup_types_empty(self):
#         types = subdivisions.lookup_types("")
#         assert types == []

#     def test_lookup_types_invalid_country(self):
#         types = subdivisions.lookup_types("ZZZ")
#         assert types == []


# class TestSubdivisionLookup:
#     def test_lookup_by_exact_name(self):
#         results = subdivisions.lookup("California")
#         assert results, "Expected at least one subdivision for 'California'"
#         assert any(s.name == "California" for s in results)

#     def test_lookup_by_exact_iso_code(self):
#         results = subdivisions.lookup("US-CA")
#         assert results, "Expected at least one subdivision for ISO code 'CA'"
#         assert any(s.code == "CA" for s in results)

#     def test_lookup_by_alpha2_code(self):
#         results = subdivisions.lookup("CA")
#         assert results, "Expected at least one subdivision for alpha-2 code 'CA'"
#         assert any(s.alpha2 == "CA" for s in results)

#     def test_lookup_case_insensitivity(self):
#         results = subdivisions.lookup("CALIFORNIA")
#         assert results, "Expected at least one subdivision for 'California'"
#         assert any(
#             s.name == "California" for s in results
#         ), "Lookup should be case insensitive"

#     def test_lookup_no_results(self):
#         results = subdivisions.lookup("NonExistentSubdivision")
#         assert results == [], "Expected no results for nonexistent subdivision"

#     def test_lookup_multiple_results(self):
#         # This depends on your data having subdivisions with overlapping names or codes
#         results = subdivisions.lookup("New York")
#         assert len(results) >= 1
#         names = [s.name for s in results]
#         assert (
#             "New York" in names or "New York City" in names or "New York State" in names
#         )
