import pytest
from villager import subdivisions, Subdivision
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
        assert all(any(alt_name in name for name in r.alt_names) for r in results)
