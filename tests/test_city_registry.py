import pytest
from villager import cities, City
from utils import select_random


class TestLoading:
    """LOADING"""

    def test_disabled(self):
        """should throw RuntimeError when attempting to use while registry is disabled."""

        cities._loaded = False  # dangerzone: don't do this!
        try:
            cities.get(id=1)
        except RuntimeError as e:
            cities._loaded = True  # or this!
            assert e


@pytest.fixture
def city() -> City:
    return select_random(cities)


@pytest.fixture(scope="session")
def enable():
    cities.enable()


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
