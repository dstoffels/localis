import pytest
from villager import countries, subdivisions, cities
from villager.registries import Registry
from villager.dtos import DTO
from utils import select_random, mangle
import random
import json
import warnings


@pytest.fixture(autouse=True)
def test_load_warning():
    if not cities._loaded:
        warnings.warn("Cities not loaded, test cancelled")
        pytest.skip("Cities not loaded, test cancelled")


REGISTRIES = [countries, subdivisions, cities]


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestGet:
    """GET"""

    def test_none(self, registry: Registry):
        """should return None if no match found"""
        result = registry.get(id=-1)
        assert result is None

    def test_kwargs(self, registry: Registry):
        """should return None if given an invalid kwarg"""
        result = registry.get(pid=1)
        assert result is None


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestFilter:
    """FILTER"""

    def test_none(self, registry: Registry):
        """should return [] if no matches are found"""
        results = registry.filter("asjh238gjs")
        assert results == []

    def test_kwargs(self, registry: Registry):
        """should return [] if given an invalid kwarg"""
        results = registry.filter(pid="1234")
        assert results == []

    def test_limit(self, registry: Registry):
        """should limit the number of results"""
        results = registry.filter("be", limit=1)
        assert len(results) == 1

    def test_query(self, registry: Registry):
        """should return a list of objects where at least one field contains the input query"""
        query = "Andorra"
        results: list[DTO] = registry.filter(query)
        assert len(results) > 0
        assert all(
            any(query.lower() in str(value).lower() for value in r.to_dict().values())
            for r in results
        ), "All results should have at least one field containing the query"

    def test_by_name(self, registry: Registry):
        """should return a list of objects where the name field contains the name kwarg"""
        name = "Andorra"
        results: list[DTO] = registry.filter(name=name)
        assert len(results) > 0, "should have at least 1 result"
        assert all(name in r.name for r in results)


@pytest.mark.parametrize("registry", REGISTRIES, ids=lambda r: type(r).__name__)
class TestSearch:
    """SEARCH"""

    def test_empty(self, registry: Registry):
        """should return [] with bad or no input."""

        bad_queries = ["", "zzzzzzzzz", "!@#$%"]
        for q in bad_queries:
            results = registry.search(q)
            assert isinstance(results, list)
            assert (
                not results
            ), f"query: {q} should yield [], instead returned {results}"

    def test_exact(self, registry: Registry):
        """should return results containing the input subject."""

        subject = select_random(registry)
        results = registry.search(subject.name, limit=10)

        assert any(subject.name == r.name for r, score in results)

    def test_mangled_name(self, registry: Registry):
        """should return results containing the input subject with a success rate > 80%."""
        COUNT = 20
        SEED = 42

        rng = random.Random(SEED)
        ids = rng.sample(range(1, registry.count), k=COUNT)

        successes = 0
        failures = []

        for i, id in enumerate(ids):
            subject: DTO = registry.get(id=id)
            mangled_query = mangle(subject.name, seed=SEED + i)
            results: list[tuple[DTO, float]] = registry.search(mangled_query, limit=10)

            if any(subject.id == r.id for r, score in results):
                successes += 1
            else:
                failures.append(
                    {
                        "original": subject.name,
                        "mangled": mangled_query,
                        "expected_id": subject.id,
                        "resulting_ids": [r.id for r, _ in results],
                    }
                )

        success_rate = successes / COUNT

        assert success_rate >= 0.8, (
            f"Success rate: {success_rate:.1%}/80%. "
            f"Successes: {successes}/{COUNT}. "
            f"Sample failures: {json.dumps(failures, indent=4, ensure_ascii=False)}"
        )

    def test_mangled_alt_name(self, registry: Registry):
        """should return results containing the input subject by one if its alternate names with a success rate > 80%"""
        COUNT = 20
        SEED = 100

        rng = random.Random(SEED)
        searched = 0
        id = 1
        successes = 0
        failures = []

        while searched < COUNT:
            subject: DTO = registry.get(id=id)
            if subject.alt_names:
                rand_alt_name = random.Random(SEED).choice(subject.alt_names)
                mangled_alt_name = mangle(rand_alt_name, seed=SEED + id)

                # slightly more relaxed limit since alt names is noisier
                results: list[tuple[DTO, float]] = registry.search(
                    mangled_alt_name, limit=15
                )

                if any(subject.id == r.id for r, score in results):
                    successes += 1
                else:
                    failures.append(
                        {
                            "original": "|".join(subject.alt_names),
                            "mangled": mangled_alt_name,
                            "expected_id": subject.id,
                            "resulting_ids": [r.id for r, _ in results],
                        }
                    )
                searched += 1
            id += 1

        success_rate = successes / COUNT

        assert success_rate >= 0.8, (
            f"Success rate: {success_rate:.1%}/80%. "
            f"Successes: {successes}/{COUNT}. "
            f"Sample failures: {json.dumps(failures, indent=4, ensure_ascii=False)}"
        )
