import threading
from concurrent.futures import ThreadPoolExecutor
import pytest
from localis.registries import QueryableRegistry
from localis.entities import Entity
from utils import queryable_registry_param

THREADS = 8
SUBJECTS = 20


def _calls(registry: QueryableRegistry, subjects: list[Entity]) -> list[tuple]:
    """Each subject's search, filter, lookup and get results, reduced to ids and scores."""
    results = []
    for subject in subjects:
        got = registry.get(subject.id)
        looked_up = registry.lookup(subject.name)
        results.append(
            (
                [(r.id, score) for r, score in registry.search(subject.name)],
                [r.id for r in registry.filter(name=subject.name)],
                looked_up.id if looked_up else None,
                got.id if got else None,
            )
        )
    return results


@queryable_registry_param
class TestConcurrency:
    """CONCURRENCY"""

    @pytest.mark.slow
    def test_shared_registry(self, registry: QueryableRegistry, select_random):
        """should give every thread sharing a registry the same results as a serial run, including threads that reach a cold registry together"""
        subjects = [select_random(registry, offset) for offset in range(SUBJECTS)]
        expected = _calls(registry, subjects)

        # cold again, so the threads race to load the dataset and every index
        registry.invalidate_cache()
        barrier = threading.Barrier(THREADS)

        def run() -> list[tuple]:
            barrier.wait()
            return _calls(registry, subjects)

        with ThreadPoolExecutor(THREADS) as pool:
            results = [future.result() for future in [pool.submit(run) for _ in range(THREADS)]]

        for result in results:
            assert result == expected, "a thread's results differ from the serial run"
