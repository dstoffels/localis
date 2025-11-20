import pytest
import warnings
from villager import cities, City, countries, subdivisions
from utils import select_random


@pytest.fixture(autouse=True)
def test_load_warning():
    if not cities._loaded:
        warnings.warn("Cities not loaded, test cancelled")
        pytest.skip("Cities not loaded, test cancelled")


class TestLoading:
    """LOADING"""

    def test_disabled(self):
        """should throw RuntimeError when attempting to use while registry is disabled."""
        loaded = cities._loaded
        if loaded:
            cities._loaded = False  # dangerzone: don't do this!
        try:
            cities.get(id=1)
        except RuntimeError as e:
            cities._loaded = loaded  # return to previous state
            assert e
            return
        assert False, "Error not thrown"

    # def test_unload(self):
    #     """should drop cities table and throw Runtime Error if cities is accessed"""
    #     if not cities._loaded:
    #         cities.load()

    #     cities.unload()

    #     assert cities._loaded == False

    #     e = None
    #     try:
    #         cities.count == 0
    #     except RuntimeError as e:
    #         assert e
    #         return
    #     assert False, "Should throw runtime error"

    # def test_load(self):
    #     """should download, create cities table and ingest fixture"""

    #     if cities._loaded:
    #         cities.unload()

    #     cities.load()

    #     assert cities._loaded
    #     assert cities.count > 0


@pytest.fixture
def city() -> City:
    return select_random(cities)


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "geonames_id"])
    def test_get(self, field: str, city: City):
        """should fetch city by:"""
        value = getattr(city, field)
        kwarg = {field: value}
        result = cities.get(**kwarg)
        assert isinstance(result, City)
        assert getattr(result, field) == value


class TestFilter:
    """FILTER"""

    def test_country(self, city: City):
        """should return a list of cities where its country contains the country kwarg"""
        results = cities.filter(country=city.country)

        assert len(results) > 0, "should return at least 1"
        assert all(city.country in r.country for r in results)

    @pytest.mark.parametrize("index", [0, 1])
    def test_admin(self, index: int, city: City):
        """should return a list of cities where its admin field contains the input admin kwarg"""

        # ensure we have an admin1 to choose from
        while not len(city.subdivisions) > 1:
            city = select_random(cities)

        sub_name = city.subdivisions[index].name

        if index == 0:
            results = cities.filter(admin1=sub_name)
        elif index == 1:
            results = cities.filter(admin2=sub_name)

        assert len(results) > 0
        assert all(sub_name == r.subdivisions[index].name for r in results)

    def test_alt_names(self, city: City):
        """should return a list of cities where the alt names contain the alt_name kwarg"""
        while not city.alt_names:
            city = select_random(cities)

        alt_name = city.alt_names[0]
        results = cities.filter(alt_name=alt_name)

        assert len(results) > 0, f"should have at least 1 result, RESULTS{results}"
        assert all(
            any(alt_name in name or alt_name == name for name in r.alt_names)
            for r in results
        ), f"alt_name: {alt_name}"


class TestForCountry:
    """FOR_COUNTRY"""

    def test_empty(self, city: City):
        """should return [] for invalid inputs"""

        results = cities.for_country(alpha2="abcbbd")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_country_and_pop_filters(self, city: City):
        """should return a population-filtered list of cities that all contain the input country code"""

        country = countries.get(alpha2=city.country_alpha2)
        filters = ["population__gt", "population__lt", None]

        for field in countries.ID_FIELDS:
            for filter in filters:
                cmap = {field: getattr(country, field)}
                fmap = {filter: city.population} if filter is not None else {}
                results = cities.for_country(**cmap, **fmap)

                if filter is not None:
                    if "__gt" in filter:
                        assert all(city.population < r.population for r in results)
                    elif "__lt" in filter:
                        assert all(city.population > r.population for r in results)

                assert len(results) > 0
                assert all(city.country_alpha2 == r.country_alpha2 for r in results)


class TestForSubdivision:
    """FOR_SUBDIVISION"""

    def test_empty(self, city: City):
        """should return [] for invalid inputs"""

        inputs = [None, "", "9999999999"]

        for field in subdivisions.ID_FIELDS:
            for input in inputs:
                map = {field: input}
                results = cities.for_subdivision(**map)
                assert results == []

    def test_sub_and_pop_filters(self, city: City):
        """should return a population-filtered list of cities that all contain the input subdivision id"""

        while not city.subdivisions:
            city = cities.get(city.id + 1)
        else:
            admin1 = city.subdivisions[0]
            if admin1.geonames_code:
                sub = subdivisions.get(geonames_code=admin1.geonames_code)
            elif admin1.iso_code:
                sub = subdivisions.get(iso_code=admin1.iso_code)

        filters = ["population__gt", "population__lt", None]

        for field in subdivisions.ID_FIELDS:
            for filter in filters:
                smap = {field: getattr(sub, field)}
                fmap = {filter: city.population} if filter is not None else {}
                results = cities.for_subdivision(**smap, **fmap)

                assert len(results) > 0

                if filter is not None:
                    if "__gt" in filter:
                        assert all(city.population < r.population for r in results)
                    elif "__lt" in filter:
                        assert all(city.population > r.population for r in results)

                assert all(city.country_alpha2 == r.country_alpha2 for r in results)
