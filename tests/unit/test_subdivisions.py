import pytest
from localis import subdivisions, Subdivision, Country


class TestGet:
    """GET"""

    @pytest.mark.parametrize("field", ["id", "geonames_code", "iso_code"])
    def test_get(self, field: str, sub: Subdivision, select_random):
        """should fetch a subdivision by field:"""

        # need to pick one with all fields
        i = 1
        while not getattr(sub, field):
            sub = select_random(reg=subdivisions, seed_offset=i)
            i += 1
        # while not sub.geonames_code or not sub.iso_code:
        #     sub = select_random(subdivisions)

        value = getattr(sub, field)
        kwarg = {field: value}
        result = subdivisions.get(**kwarg)

        assert isinstance(result, Subdivision)
        assert getattr(result, field) == value


class TestFilter:
    """FILTER"""

    @pytest.mark.parametrize("field", ["type", "country"])
    def test_fields(self, field: str):
        """should return a list of subdivisions where the field kwarg is in:"""

        sub = subdivisions.get(id=1)  # Andorra La Vella
        value = getattr(sub, field)
        results = subdivisions.filter(**{field: value})

        assert len(results) > 0, "should return at least 1"
        assert sub in results, "subject should be in results"

    def test_alt_names(self):
        """should return a list of subdivisions where its alt_names field contains the alt_name kwarg"""

        sub = subdivisions.get(id=7)  # Saint Julia de Loria

        alt_name = sub.alt_names[0]  # grab the first alias
        results = subdivisions.filter(alt_name=alt_name)

        assert len(results) > 0, "should return at least 1"
        assert sub in results


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

    def test_admin_level_filter(self):
        """should return a country's subdivisions filtered by admin level with the default being 1"""

        results = subdivisions.for_country(alpha2="US")

        assert len(results) > 0, f"expected at least one result (admin1)"
        assert all(
            r.admin_level == 1 for r in results
        ), f"expected only admin1 subdivisions {results}"

        results = subdivisions.for_country(alpha2="US", admin_level=2)

        assert len(results) > 0, f"expected at least one result (admin2) "
        assert all(
            r.admin_level == 2 for r in results
        ), f"expected only admin2 subdivisions {results}"


class TestTypes:
    """TYPES_FOR_COUNTRY"""

    def test_empty(self, sub: Subdivision):
        """should reutrn [] with invalid input"""

        results = subdivisions.types_for_country(alpha2="abcbbd")

        assert isinstance(results, list)
        assert len(results) == 0

    def test_all_types(self, country: Country):
        """should return a list of distinct types for a given country"""

        results = subdivisions.types_for_country(alpha2=country.alpha2)

        subs = subdivisions.filter(country=country.alpha2)
        sub = None
        for s in subs:
            sub = s
            if s.type in results:
                break

        assert (
            sub.type in results if sub and sub.type is not None else True
        ), f"expected subdivision's type ({sub.type}) to be in the results (if type isn't null): {results}"

    @pytest.mark.parametrize("admin_level", [1, 2])
    def test_admin_lvl_filter(self, admin_level, country: Country):
        """should return a list of distinct types for a given country, filtered by admin_level"""

        results = subdivisions.types_for_country(
            alpha2=country.alpha2, admin_level=admin_level
        )

        filtered_subs = subdivisions.for_country(
            alpha2=country.alpha2, admin_level=admin_level
        )

        filtered_type_set = set(
            [
                s.type
                for s in filtered_subs
                if s.type is not None and s.admin_level == admin_level
            ]
        )

        assert (
            set(results) == filtered_type_set
        ), f"expected the results to match the set of types from filtered subdivisions"
