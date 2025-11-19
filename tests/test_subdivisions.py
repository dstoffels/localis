import pytest
from villager import subdivisions, Subdivision, countries
from utils import select_random


@pytest.fixture
def sub() -> Subdivision:
    return select_random(subdivisions)


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "geonames_code", "iso_code"])
    def test_get(self, field: str, sub: Subdivision):
        """should fetch a subdivision by:"""

        # need to pick one with all fields
        while not sub.geonames_code or not sub.iso_code:
            sub = select_random(subdivisions)

        value = getattr(sub, field)
        kwarg = {field: value}
        result = subdivisions.get(**kwarg)

        assert isinstance(result, Subdivision)
        assert getattr(result, field) == value

    def _fringe_case(self, sub: Subdivision):
        """"""

        # TODO: RS.SE does not match to due constituent (admin2) subs returning first, need to refactor model, expressions and fields to accommodate.


class TestFilter:
    """FILTER"""

    @pytest.mark.parametrize("field", ["type", "country"])
    def test_fields(self, field: str, sub: Subdivision):
        """should return a list of subdivisions where the field kwarg is in:"""

        # need to pick one with all fields
        while not sub.type or not sub.country:
            sub = select_random(subdivisions)

        value = getattr(sub, field)
        kwarg = {field: value}
        results = subdivisions.filter(**kwarg)

        assert len(results) > 0, "should return at least 1"
        assert all(value in getattr(r, field) for r in results)

    def test_alt_names(self, sub: Subdivision):
        """should return a list of subdivisions where its alt_names field contains the alt_name kwarg"""

        # need to pick on with alt_names
        while not sub.alt_names:
            sub = select_random(subdivisions)

        alt_name = sub.alt_names[0]
        results = subdivisions.filter(alt_name=alt_name)

        assert len(results) > 0, "should return at least 1"
        assert all(
            any(alt_name in name or alt_name == name for name in r.alt_names)
            for r in results
        )


class TestForCountry:
    """FOR_COUNTRY"""

    def test_empty(self, sub: Subdivision):
        """should return [] with invalid input"""

        results = subdivisions.for_country(alpha2="abcbbd")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_country_code(self, sub: Subdivision):
        """should return a list of subdivisions all of which contain the input country code"""

        results = subdivisions.for_country(alpha2=sub.country_alpha2)

        assert len(results) > 0
        assert all(sub.country_alpha2 == r.country_alpha2 for r in results)

    def test_admin_level_filter(self, sub: Subdivision):
        """should return a country's subdivisions filtered by admin level with the default being 1"""

        results = subdivisions.for_country(alpha2=sub.country_alpha2)

        assert len(results) > 0
        assert all(r.admin_level == 1 for r in results)

        results = subdivisions.for_country(alpha2=sub.country_alpha2, admin_level=2)

        assert len(results) > 0
        assert all(r.admin_level == 2 for r in results)


class TestTypes:
    """TYPES_FOR_COUNTRY"""

    def test_empty(self, sub: Subdivision):
        """should reutrn [] with invalid input"""

        results = subdivisions.types_for_country(alpha2="abcbbd")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_country_and_admin_level(self, sub: Subdivision):
        """should return a list of distinct types for a given country, filtered by admin_level"""

        country = countries.get(alpha2=sub.country_alpha2)
        admin_levels = [None, 1, 2]

        for field in countries.ID_FIELDS:
            map = {field: getattr(country, field)}

            for lvl in admin_levels:
                results = subdivisions.types_for_country(admin_level=lvl, **map)
                filtered_subs = subdivisions.for_country(admin_level=lvl, **map)

                filtered_subs_type_set = set(
                    [
                        s.type
                        for s in filtered_subs
                        if s.type is not None and s.admin_level == lvl
                    ]
                )

                assert len(results) == len(filtered_subs_type_set)
                assert set(results) == filtered_subs_type_set
