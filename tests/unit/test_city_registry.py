import pytest
from localis import cities


class TestPopulationThreshold:
    """POPULATION THRESHOLD"""

    def test_filters_cache(self):
        """should exclude every city below the threshold from the cache once set, and restore the full cache once cleared"""
        full_count = len(cities)
        threshold = 100_000
        try:
            cities.set_population_threshold(threshold)
            filtered = list(cities)
            assert len(filtered) < full_count, "threshold should have excluded some cities"
            assert all(city.population >= threshold for city in filtered)
        finally:
            cities.set_population_threshold(None)
            assert len(cities) == full_count

    def test_filters_indexes(self):
        """should exclude a below-threshold city from lookup(), filter(), and search() once the threshold is set, and restore access to it once cleared"""
        geonames_id = 3040686  # Encamp, population 11223
        threshold = 100_000

        encamp = cities.lookup(geonames_id)
        assert encamp is not None
        assert encamp.population == 11223

        try:
            cities.set_population_threshold(threshold)

            assert cities.lookup(geonames_id) is None

            filter_results = cities.filter(name=encamp.name)
            assert encamp.id not in [c.id for c in filter_results]

            search_results = cities.search(encamp.name)
            assert encamp.id not in [c.id for c, _ in search_results]
        finally:
            cities.set_population_threshold(None)
            assert cities.lookup(geonames_id) is not None

    @pytest.mark.parametrize("bad_threshold, error", [("15000", TypeError), (1.5, TypeError), (True, TypeError), (-1, ValueError)])
    def test_bad_threshold(self, bad_threshold, error):
        """should raise when set, rather than on first access, for a threshold that isn't a non-negative int, leaving the current one in place"""
        with pytest.raises(error):
            cities.set_population_threshold(bad_threshold)
        assert cities.population_threshold is None

    def test_same_threshold_keeps_cache(self):
        """should keep the loaded cache when the threshold set is the one already in place"""
        cache = cities._cache
        cities.set_population_threshold(None)
        assert cities._cache is cache
