from localis import countries
from localis.entities import Country


class TestHistoricCountries:
    """HISTORIC COUNTRIES"""

    def test_excluded_from_iteration_by_default(self) -> None:
        """should leave every historic entry out of iteration by default, and yield at least one once included"""
        assert (
            countries.include_historic is False
        ), "include_historic should be False by default"
        assert all(
            c.historic is None for c in countries
        ), "no historic entries should appear in the registry by default"

        try:
            countries.set_include_historic(True)
            assert (
                countries.include_historic is True
            ), "include_historic should be True after setting it"
            assert any(
                c.historic is not None for c in countries
            ), "at least one historic entry should appear in the registry when included"
        finally:
            countries.set_include_historic(False)

    def test_len_follows_include_historic(self) -> None:
        """should count in len() the records iteration yields with historic entries included, more than without"""
        default_len = len(countries)
        try:
            countries.set_include_historic(True)
            assert len(countries) == sum(1 for _ in countries)
            assert len(countries) > default_len
        finally:
            countries.set_include_historic(False)

    def test_filter_search_exclusion(self, historic_country: Country) -> None:
        """should keep a historic country's name from surfacing via filter()/search() by default, and surface it once included"""
        assert historic_country.name not in [
            c.name for c in countries.filter(name=historic_country.name)
        ]
        assert historic_country.name not in [
            c.name for c, _ in countries.search(historic_country.name)
        ]

        try:
            countries.set_include_historic(True)
            assert historic_country.name in [
                c.name for c in countries.filter(name=historic_country.name)
            ]
            assert historic_country.name in [
                c.name for c, _ in countries.search(historic_country.name)
            ]
        finally:
            countries.set_include_historic(False)

    def test_get_and_lookup_bypass(self, historic_country: Country) -> None:
        """should resolve a historic entry through get() and lookup() regardless of include_historic"""
        assert historic_country.historic is not None
        by_lookup: Country | None = countries.lookup(historic_country.historic.alpha_4)

        assert (
            by_lookup is not None and by_lookup.id == historic_country.id
        ), f"lookup() should resolve a historic entry regardless of include_historic: {by_lookup}"

        by_get: Country | None = countries.get(historic_country.id)

        assert (
            by_get is not None and by_get.id == historic_country.id
        ), "get() should resolve a historic entry regardless of include_historic"
