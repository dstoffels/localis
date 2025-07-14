from villager import localities, Locality
from utils import mangle
import pytest
import time


@pytest.fixture(autouse=True)
def track_test_metrics(request):
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start
    print(f"\nTest {request.node.name} took {duration:.3f}s")


class TestGet:
    def setup_method(self):
        self.locality_sample: list[Locality] = [l for l in localities]

    def test_id(self):
        for l in self.locality_sample[:1000]:
            locality = localities.get(l.villager_id)
            assert isinstance(locality, Locality)
            assert locality is not None
            assert l.name == locality.name

    def test_id_long_type(self):
        test = localities[0]
        locality = localities.get(f"way:{test.osm_id}")

        assert isinstance(locality, Locality)
        assert locality is not None
        assert test.name == locality.name

    def test_normalized(self):
        test = localities[0]
        locality = localities.get(f"   {test.villager_id.upper()}   ")
        assert isinstance(locality, Locality)
        assert locality is not None
        assert test.name == locality.name


class TestLookup:
    def test_lookup(self):
        for l in localities[:100]:
            results = localities.lookup(l.name)
            assert results
            assert isinstance(results, list)
            assert len(results) > 0
            assert l.name in [r.name for r in results]

    def test_is_normalized(self):
        test = localities[0]
        results = localities.lookup(f"   {test.name.upper()}   ")
        assert isinstance(results, list)
        assert results, "Expected at least one result"
        assert test.name in [r.name for r in results]


class TestSearch:
    def setup_method(self):
        self.locality_sample: list[Locality] = localities[:10000]

    def test_fuzzy_name_top10(self, request):
        seeds = range(20)
        success_count = 0
        total = 0
        typo_rate = 0.15
        success_threshold = 0.6
        for seed in seeds:
            for l in self.locality_sample:
                test = mangle(l.name, typo_rate, seed)
                results = localities.search(test, limit=10)
                total += 1

                if not results:
                    continue

                if l.name in [r.name for r in results]:
                    success_count += 1
        accuracy = success_count / total
        print(f"\n{success_count} / {total} = {accuracy:.2%} accuracy")
        assert (
            accuracy >= success_threshold
        ), f"{accuracy:.2%} accuracy below threshold {success_threshold:.2%}"

    def test_fuzzy_match_by_subdivision(self, request):
        seeds = range(20)
        success_count = 0
        total = 0
        typo_rate = 0.15
        success_threshold = 0.8

        for seed in seeds:
            for l in self.locality_sample:
                sub = l.subdivisions[len(l.subdivisions) - 1]
                test = mangle(l.name, typo_rate, seed)
                results = localities.search(f"{test} {sub.name}")
                total += 1
                if not results:
                    continue
                if l.name in [r.name for r in results]:
                    success_count += 1
        accuracy = success_count / total
        print(f"\n{success_count} / {total} = {accuracy:.2%} accuracy")
        assert (
            accuracy >= success_threshold
        ), f"{accuracy:.2%} accuracy below threshold {success_threshold:.2%}"

    def test_fuzzy_match_by_country(self, request):
        seeds = range(20)
        success_count = 0
        total = 0
        typo_rate = 0.15
        success_threshold = 0.7

        for seed in seeds:
            for l in self.locality_sample:
                test = mangle(f"{l.name}", typo_rate, seed)
                results = localities.search(f"{test} {l.country}")
                total += 1
                if not results:
                    continue
                if l.name in [r.name for r in results]:
                    success_count += 1
        accuracy = success_count / total
        print(f"\n{success_count} / {total} = {accuracy:.2%} accuracy")
        assert (
            accuracy >= success_threshold
        ), f"{accuracy:.2%} accuracy below threshold {success_threshold:.2%}"
