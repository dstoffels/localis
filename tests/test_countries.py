import pytest
from villager import countries, Country
import random


class TestGet:
    def test_alpha2(self):
        for c in countries:
            country = countries.get(c.alpha2)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha2 == country.alpha2

    def test_alpha3(self):
        for c in countries:
            country = countries.get(c.alpha3)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha3 == country.alpha3

    def test_numeric(self):
        for c in countries:
            country = countries.get(c.numeric)
            assert isinstance(country, Country)
            assert country is not None
            assert c.numeric == country.numeric

    def test_aliases(self):
        for alias, alpha_2 in countries.CODE_ALIASES.items():
            country = countries.get(alias)
            assert isinstance(country, Country)
            assert country is not None
            assert country.alpha2 == alpha_2

    def test_is_normalized(self):
        for c in countries:
            test = f"   {'.'.join(c.alpha2.split()).lower()}   "
            country = countries.get(test)
            assert isinstance(country, Country)
            assert country is not None
            assert c.alpha2 == country.alpha2

    def test_none(self):
        country = countries.get("ZZZ")
        assert country is None


class TestLookup:
    def test_lookup(self):
        for c in countries:
            results = countries.lookup(c.name)
            assert results
            assert len(results) > 0
            country = results[0]
            assert country.name == c.name

    def test_dupes(self):
        results = countries.lookup("Congo")
        alpha2s = [result.alpha2 for result in results]
        assert len(results) == 2
        assert "CG" in alpha2s
        assert "CD" in alpha2s

    def test_aliases(self):
        for alias, name in countries.ALIASES.items():
            results = countries.lookup(alias)
            assert results
            assert len(results) > 0
            country = results[0]
            assert country.name == name

    def test_is_normalized(self):
        for c in countries:
            results = countries.lookup(f"   {c.name.lower()}   ")
            assert results
            assert len(results) > 0
            country = results[0]
            assert country.name == c.name

    def test_none(self):
        results = countries.lookup("california")
        assert results == []


class TestSearch:
    def test_none(self):
        results = countries.search("")
        assert results == []

    def test_exact_ranks_first(self):
        for c in countries:
            results = countries.search(c.name)
            assert results
            country, score = results[0]
            assert country.name == c.name
            assert score == 1

            results = countries.search(c.alpha2)
            assert results
            country, score = results[0]
            assert country.alpha2 == c.alpha2
            assert score == 1

            results = countries.search(c.alpha3)
            assert results
            country, score = results[0]
            assert country.alpha3 == c.alpha3
            assert score == 1

    def test_handles_minor_typos(self):
        for c in countries:
            test = self.mangle(c.name, 0.4, 154551)
            print(c.name, ":", test)
            results = countries.search(test)
            assert results
            country, score = results[0]
            print("result:", country.name, score)
            print([(c.name, score) for c, score in results])
            assert c.name == country.name
            assert score > 0
            assert score <= 1

    alphabet = "abcdefghijklmnopqrstuvwxyz"

    def mangle(self, s: str, typo_chance: float = 0.15, seed: int = 42) -> str:
        rng = random.Random(seed)
        if not s or len(s) < 3:
            return s

        s_list = list(s)
        typo_ops = ["swap", "replace"]
        num_typos = max(1, int(len(s) * typo_chance))
        applied = 0
        positions = set()

        while applied < num_typos:
            i = rng.randint(1, len(s_list) - 2)
            if i in positions or s_list[i].isspace():
                continue

            op = rng.choice(typo_ops)
            if op == "swap" and i < len(s_list) - 1 and not s_list[i + 1].isspace():
                s_list[i], s_list[i + 1] = s_list[i + 1], s_list[i]
            elif op == "replace":
                s_list[i] = rng.choice("abcdefghijklmnopqrstuvwxyz")

            positions.add(i)
            applied += 1

        return "".join(s_list)


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
