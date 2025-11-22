import pytest
from localis import cities, City, subdivisions, Subdivision, Country


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "geonames_id"])
    def test_get(self, field: str, city: City):
        """should fetch city by:"""
        value = getattr(city, field)
        kwarg = {field: value}
        result = cities.get(**kwarg)
        assert isinstance(
            result, City
        ), f"should return a City, instead returned {result}. {field}: {value}"
        assert getattr(result, field) == value, f"Result: {result}, {field}: {value}"


class TestFilter:
    """FILTER"""

    def test_country(self, city: City):
        """should return a list of cities where its country contains the country kwarg"""
        results = cities.filter(country=city.country, limit=10)

        assert len(results) > 0, "should return at least 1"
        assert all(city.country in r.country for r in results)

    @pytest.mark.parametrize("index", [0, 1])
    def test_admin(self, index: int, city: City, select_random):
        """should return a list of cities where its admin field contains the input admin kwarg"""

        # ensure we have a subdivision to choose from
        i = 1
        while not len(city.subdivisions) > index:
            city = select_random(cities, i)
            i += 1

        sub_name = city.subdivisions[index].name

        if index == 0:
            results = cities.filter(admin1=sub_name)
        elif index == 1:
            results = cities.filter(admin2=sub_name)

        assert len(results) > 0
        assert any(
            sub_name == r.subdivisions[index].name
            or sub_name in r.subdivisions[index].name
            for r in results
        ), f"Searched cities for {sub_name}, got back {set([s.subdivisions[index].name for s in results])}"


class TestForCountry:
    """FOR_COUNTRY"""

    def test_empty(self):
        """should return [] for invalid inputs"""

        results = cities.for_country(alpha2="abcbbd")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_filtering(self, country: Country):
        """should return list of cities for a given country"""

        results = cities.for_country(alpha2=country.alpha2)

        assert results, f"expected at least 1 result: {results}"
        assert all(
            country.name == r.country for r in results
        ), f"expected all results to match the subject country name: {country.name}, got {set([r.subdivisions for r in results])}"

    @pytest.mark.parametrize("filter", ["population__gt", "population__lt"])
    def test_pop_filters(self, filter: str, city: City, country: Country):
        """should return a population-filtered list of cities"""

        kwargs = {filter: city.population, "alpha2": country.alpha2}

        results = cities.for_country(**kwargs)

        if "__gt" in filter:
            assert all(city.population < r.population for r in results)
        elif "__lt" in filter:
            assert all(city.population > r.population for r in results)


class TestForSubdivision:
    """FOR_SUBDIVISION"""

    @pytest.mark.parametrize("bad_input", [None, "", "9999999999"])
    def test_empty(self, bad_input):
        """should return [] for invalid inputs"""

        for field in subdivisions.ID_FIELDS:
            map = {field: bad_input}
            results = cities.for_subdivision(**map)
            assert results == []

    def test_filtering(self, sub: Subdivision):
        """should return a filtered list of cities for a given subdivision"""

        kwargs = {}
        if sub.geonames_code:
            kwargs["geonames_code"] = sub.geonames_code
        elif sub.iso_code:
            kwargs["iso_code"] = sub.iso_code

        results = cities.for_subdivision(**kwargs)

        assert all(
            sub.name in s.name
            for r in results
            for s in r.subdivisions
            if s.admin_level == sub.admin_level
        ), f"expected results' subdivisions lists to contain the input subdivision: {sub.name}, got {set([s.name for r in results for s in r.subdivisions])}"

    @pytest.mark.parametrize("filter", ["population__gt", "population__lt"])
    def test_pop_filters(self, city: City, sub: Subdivision, filter: str):
        """should return a population-filtered list of cities"""

        kwargs = {filter: city.population}
        if sub.geonames_code:
            kwargs["geonames_code"] = sub.geonames_code
        elif sub.iso_code:
            kwargs["iso_code"] = sub.iso_code

        results = cities.for_subdivision(**kwargs)

        if "__gt" in filter:
            assert all(city.population < r.population for r in results)
        elif "__lt" in filter:
            assert all(city.population > r.population for r in results)
