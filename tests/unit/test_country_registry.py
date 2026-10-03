from localis import countries
from localis.entities import Country, HistoricInfo


class TestHistoricCountries:
    def test_excluded_from_iteration_by_default(self) -> None:
        """no historic entry should appear in iteration by default, and at least one should once included"""
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

    def test_filter_search_exclusion(self, historic_country: Country) -> None:
        """a historic country's name should not surface via filter()/search() by default, and should once included"""
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
        """get() and lookup() should resolve a historic entry regardless of include_historic"""
        assert historic_country.historic is not None
        by_lookup: Country | None = countries.lookup(historic_country.historic.alpha_4)

        assert (
            by_lookup is not None
        ), f"lookup() should resolve a historic entry regardless of include_historic: {by_lookup}"

        by_get: Country | None = countries.get(by_lookup.id)

        assert (
            by_get is not None
        ), "get() should resolve a historic entry regardless of include_historic"
