from villager.registries.registry import Registry
from villager.db import CountryModel, Country, db
from villager.literals import CountryCode, CountryName, CountryNumeric
from villager.utils import normalize


class CountryRegistry(Registry[CountryModel, Country]):
    """
    Registry for managing Country entities.

    Supports get by alpha2, alpha3 & numeric codes, lookup by country name with support for some aliases/former names,
    and fuzzy search.
    """

    def get(self, identifier: CountryCode | CountryNumeric) -> Country | None:
        if not identifier:
            return None

        identifier = normalize(identifier)

        if isinstance(identifier, int):
            row = self._model_cls.get(CountryModel.numeric == identifier)
        else:
            identifier = self.CODE_ALIASES.get(identifier.lower(), identifier)
            row = self._model_cls.get(
                (CountryModel.alpha2 == identifier)
                | (CountryModel.alpha3 == identifier)
            )

        if row:
            return row.dto

    def lookup(self, identifier: CountryName, **kwargs) -> list[Country]:
        """Lookup a country by exact name."""
        if not identifier:
            return []

        identifier = self.ALIASES.get(identifier.lower(), identifier)
        identifier = normalize(identifier)

        rows = self._model_cls.select(CountryModel.normalized_name == identifier)
        return [r.dto for r in rows]

    @property
    def _sql_filter_base(self):
        return f"""SELECT c.*, f.tokens FROM countries_fts f
        JOIN countries c ON f.rowid = c.id
        """

    CODE_ALIASES = {
        "uk": "GB",
    }

    ALIASES = {
        "england": "United Kingdom",
        "scotland": "United Kingdom",
        "wales": "United Kingdom",
        "northern ireland": "United Kingdom",
        "great britain": "United Kingdom",
        "britain": "United Kingdom",
        "united states of america": "United States",
        "america": "United States",
        "czech republic": "Czechia",
        "ivory coast": "Côte d'Ivoire",
        "cote d'ivoire": "Côte d'Ivoire",
        "burma": "Myanmar",
        "swaziland": "Eswatini",
        "holland": "Netherlands",
        "macedonia": "North Macedonia",
        "cape verde": "Cabo Verde",
        "laos": "Lao People's Democratic Republic",
        "syria": "Syrian Arab Republic",
        "russia": "Russian Federation",
        "ussr": "Russian Federation",
        "soviet union": "Russian Federation",
        "vietnam": "Viet Nam",
        "zaire": "Congo",
        "brunei": "Brunei Darussalam",
        "são tomé and príncipe": "Sao Tome and Principe",
        "east timor": "Timor-Leste",
        "yugoslavia": "Serbia",
        "east germany": "Germany",
        "west germany": "Germany",
    }
