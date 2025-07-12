from villager import subdivisions, Subdivision, countries
from villager.db import SubdivisionModel, CountryModel
import random
from utils import mangle


class TestGet:
    def test_iso_code(self):
        for s in subdivisions:
            subdivision = subdivisions.get(s.iso_code)
            assert isinstance(subdivision, Subdivision)
            assert subdivision is not None
            assert s.iso_code == subdivision.iso_code

    def test_is_normalized(self):
        for s in subdivisions:
            test = f"   {s.iso_code.lower()}   "
            subdivision = subdivisions.get(test)
            assert isinstance(subdivision, Subdivision)
            assert subdivision is not None
            assert s.iso_code == subdivision.iso_code

    def test_none(self):
        subdivision = subdivisions.get("ZFGCV2")
        assert subdivision is None


class TestLookup:
    def test_lookup(self):
        for s in subdivisions:
            results = subdivisions.lookup(s.name)
            assert results
            assert isinstance(results, list)
            assert len(results) > 0
            assert s.name in [r.name for r in results]

    def test_is_normalized(self):
        for s in subdivisions:
            test = f"   {s.name.lower()}   "
            results = subdivisions.lookup(test)
            assert isinstance(results, list)
            assert results
            assert len(results) > 0
            assert s.name in [r.name for r in results]

    def test_by_country(self):
        for s in subdivisions:
            results = subdivisions.lookup(s.name, country=s.country_alpha2)
            assert isinstance(
                results, list
            ), f"Expected results to be a list for {s.name}"
            assert results, f'Expected at least one subdivision for "{s.name}"'
            assert s.name in [r.name for r in results]


class TestSearch:
    def test_none(self):
        results = subdivisions.search("")
        assert results == []

    def test_exact_matches(self):
        for s in subdivisions:
            results = subdivisions.search(s.name)
            assert isinstance(results, list)
            assert results, f'Expected at least one subdivision for "{s.name}"'
            assert len(results) > 0
            assert s.name in [r.name for r, score in results]

    def test_typos_top5(self):
        seeds = range(3)
        success_count = 0
        total = 0
        typo_rate = 0.15
        success_threshold = 0.8

        for seed in seeds:
            for s in subdivisions:
                test = mangle(f"{s.name} {s.country_alpha2}", typo_rate, seed)
                results = subdivisions.search(test)
                total += 1

                if not results:
                    continue

                if s.name in [r.name for r, score in results]:
                    success_count += 1

        accuracy = success_count / total
        assert (
            accuracy >= success_threshold
        ), f"{accuracy:.2%} accuracy below threshold {success_threshold:.2%}"

    def test_typos_by_country(self):
        seeds = range(1)
        success_count = 0
        total = 0
        typo_rate = 0.15
        success_threshold = 0.95

        for seed in seeds:
            for s in subdivisions:
                test = mangle(s.name, typo_rate, seed)
                results = subdivisions.search(test, country=s.country)
                total += 1

                if not results:
                    continue

                if s.name in [r.name for r, score in results]:
                    success_count += 1
        accuracy = success_count / total
        assert (
            accuracy >= success_threshold
        ), f"{accuracy:.2%} accuracy below threshold {success_threshold:.2%}"


class TestByCountry:
    def setup_method(self):
        self.subs_by_country: dict[str, list[Subdivision]] = {}
        for s in subdivisions:
            self.subs_by_country.setdefault(s.country_alpha2, []).append(s)

    def test_alpha2(self):
        for alpha2, expected in self.subs_by_country.items():
            results = subdivisions.by_country(alpha2)
            assert isinstance(results, list), f"Expected list for {alpha2}"
            assert len(results) == len(expected), f"Mismatched lengths for {alpha2}"
            assert results == expected, f"Results mismatch for {alpha2}"

    def test_alpha3(self):
        for alpha2, expected in self.subs_by_country.items():
            results = subdivisions.by_country(expected[0].country_alpha3)
            assert isinstance(results, list), f"Expected list for {alpha2}"
            assert len(results) == len(expected), f"Mismatched lengths for {alpha2}"
            assert results == expected, f"Results mismatch for {alpha2}"


class TestGetCategories:
    def setup_method(self):
        self.sub_cats_by_country: dict[str, set[str]] = {}
        for s in subdivisions:
            self.sub_cats_by_country.setdefault(s.country_alpha2, set()).add(s.category)

    def test_country_alpha2(self):
        for alpha2, expected in self.sub_cats_by_country.items():
            results = subdivisions.get_categories(alpha2)
            assert isinstance(results, list), f"Expected set for {alpha2}"
            assert results == list(expected), f"Results mismatch for {alpha2}"


# # for seed in seeds:
# #     for s in [s for s in subdivisions if s.country_alpha2 == "US"]:
# #         test = mangle(s.name, typo_rate, seed)
# #         results = subdivisions.search(test, s.country_alpha2)
# #         total += 1


# # class TestSubdivisionByCountry:
# #     def test_by_country_alpha2(self):
# #         results: list[Subdivision] = subdivisions.by_country("US")
# #         assert results
# #         assert all(sub.country_alpha2 == "US" for sub in results)

# #     def test_by_country_alpha3(self):
# #         results: list[Subdivision] = subdivisions.by_country("USA")
# #         assert results
# #         assert all(sub.country_alpha2 == "US" for sub in results)

# #     def test_by_country_name(self):
# #         results: list[Subdivision] = subdivisions.by_country("United States")
# #         assert results
# #         assert all(sub.country_alpha2 == "US" for sub in results)

# #     def test_by_country_case_insensitive(self):
# #         results: list[Subdivision] = subdivisions.by_country("united states")
# #         assert results
# #         assert all(sub.country_alpha2 == "US" for sub in results)

# #     def test_by_country_alias(self):
# #         results = subdivisions.by_country("UK")
# #         assert results
# #         assert all(sub.country_code == "GB" for sub in results)

# #     def test_by_country_invalid(self):
# #         results: list[Subdivision] = subdivisions.by_country("ZZ")
# #         assert results == []

# #     def test_by_country_empty(self):
# #         results: list[Subdivision] = subdivisions.by_country("")
# #         assert results == []


# # class TestSubdivisionlookupTypes:
# #     def test_lookup_types_alpha2(self):
# #         types = subdivisions.lookup_types("US")
# #         assert types
# #         assert isinstance(types, list)
# #         assert "state" in types

# #     def test_lookup_types_alpha3(self):
# #         types = subdivisions.lookup_types("USA")
# #         assert types
# #         assert isinstance(types, list)

# #     def test_lookup_types_name(self):
# #         types = subdivisions.lookup_types("United States")
# #         assert types
# #         assert isinstance(types, list)
# #         assert "state" in types or "territory" in types

# #     def test_lookup_types_uk_alias(self):
# #         types = subdivisions.lookup_types("UK")
# #         assert types
# #         assert isinstance(types, list)
# #         assert "country" in types

# #     def test_lookup_types_case_insensitivity():
# #         inputs = ["us", "USA", "uSa", "UnIteD STaTEs", "united states"]
# #         expected_types = subdivisions.lookup_types("US")

# #         for inp in inputs:
# #             types = subdivisions.lookup_types(inp)
# #             assert types == expected_types

# #     def test_lookup_types_empty(self):
# #         types = subdivisions.lookup_types("")
# #         assert types == []

# #     def test_lookup_types_invalid_country(self):
# #         types = subdivisions.lookup_types("ZZZ")
# #         assert types == []


# # class TestSubdivisionLookup:
# #     def test_lookup_by_exact_name(self):
# #         results = subdivisions.lookup("California")
# #         assert results, "Expected at least one subdivision for 'California'"
# #         assert any(s.name == "California" for s in results)

# #     def test_lookup_by_exact_iso_code(self):
# #         results = subdivisions.lookup("US-CA")
# #         assert results, "Expected at least one subdivision for ISO code 'CA'"
# #         assert any(s.code == "CA" for s in results)

# #     def test_lookup_by_alpha2_code(self):
# #         results = subdivisions.lookup("CA")
# #         assert results, "Expected at least one subdivision for alpha-2 code 'CA'"
# #         assert any(s.alpha2 == "CA" for s in results)

# #     def test_lookup_case_insensitivity(self):
# #         results = subdivisions.lookup("CALIFORNIA")
# #         assert results, "Expected at least one subdivision for 'California'"
# #         assert any(
# #             s.name == "California" for s in results
# #         ), "Lookup should be case insensitive"

# #     def test_lookup_no_results(self):
# #         results = subdivisions.lookup("NonExistentSubdivision")
# #         assert results == [], "Expected no results for nonexistent subdivision"

# #     def test_lookup_multiple_results(self):
# #         # This depends on your data having subdivisions with overlapping names or codes
# #         results = subdivisions.lookup("New York")
# #         assert len(results) >= 1
# #         names = [s.name for s in results]
# #         assert (
# #             "New York" in names or "New York City" in names or "New York State" in names
# #         )
