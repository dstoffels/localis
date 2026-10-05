import pytest
from localis import cities, countries, subdivisions, City, CityRegistry


def _registry() -> CityRegistry:
    """A cities registry of its own, so a threshold set on it never invalidates the shared cities cache."""
    return CityRegistry(countries=countries, subdivisions=subdivisions)


@pytest.fixture(scope="module")
def thresholded(city: City) -> tuple[CityRegistry, int]:
    """A registry of its own narrowed to exclude a random city, built once for the module."""
    # at least 100,000 keeps the narrowed cache small; just above the city's population so it's always excluded
    threshold = max(city.population + 1, 100_000)
    registry = _registry()
    registry.set_population_threshold(threshold)
    return registry, threshold


class TestPopulationThreshold:
    """POPULATION THRESHOLD"""

    def test_filters_cache(self, thresholded: tuple[CityRegistry, int]):
        """should exclude every city below the threshold from the cache"""
        registry, threshold = thresholded
        filtered = list(registry)

        assert len(filtered) < len(cities), "threshold should have excluded some cities"
        assert all(c.population >= threshold for c in filtered)

    def test_filters_indexes(self, city: City, thresholded: tuple[CityRegistry, int]):
        """should exclude a below-threshold city from lookup(), filter(), and search()"""
        registry, _ = thresholded

        assert registry.lookup(city.key) is None
        assert city.id not in [c.id for c in registry.filter(name=city.name)]
        assert city.id not in [c.id for c, _ in registry.search(city.name)]

    def test_change_drops_cache(self):
        """should drop the loaded cache and row filter when the threshold is cleared, so the next access loads every city"""
        registry = _registry()
        registry.set_population_threshold(1_000)
        # stands in for a loaded cache, so the test needn't load one
        vars(registry)["_cache"] = {}

        registry.set_population_threshold(None)

        assert "_cache" not in vars(registry)
        assert registry._row_filter is None

    def test_same_threshold_keeps_cache(self):
        """should keep the loaded cache when the threshold set is the one already in place"""
        registry = _registry()
        registry.set_population_threshold(1_000)
        cache = vars(registry)["_cache"] = {}

        registry.set_population_threshold(1_000)

        assert vars(registry)["_cache"] is cache

    @pytest.mark.parametrize("bad_threshold, error", [("15000", TypeError), (1.5, TypeError), (True, TypeError), (-1, ValueError)])
    def test_bad_threshold(self, bad_threshold, error):
        """should raise when set, rather than on first access, for a threshold that isn't a non-negative int, leaving the current one in place"""
        registry = _registry()
        with pytest.raises(error):
            registry.set_population_threshold(bad_threshold)
        assert registry.population_threshold is None


class TestPopulationSort:
    """POPULATION SORT"""

    def test_reorders_by_population(self, city: City):
        """should return the same matches as an unsorted search, largest population first"""
        by_score = cities.search(city.name)
        by_population = cities.search(city.name, population_sort=True)

        assert sorted(c.id for c, _ in by_population) == sorted(c.id for c, _ in by_score)
        populations = [c.population for c, _ in by_population]
        assert populations == sorted(populations, reverse=True)
