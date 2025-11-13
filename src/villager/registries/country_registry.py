from villager.registries.registry import Registry
from villager.db import CountryModel, Country
from villager.db.models.fields import Expression

# from villager.literals import CountryCode, CountryName, CountryNumeric
from villager.utils import normalize


class CountryRegistry(Registry[CountryModel, Country]):
    """
    Registry for managing Country entities.

    Supports get by alpha2, alpha3 & numeric codes, lookup by country name with support for some aliases/former names,
    and fuzzy search.
    """

    def __init__(self, model_cls):
        super().__init__(model_cls)
        self._addl_search_attrs = ["alpha2", "alpha3"]

    def get(
        self,
        *,
        id: int = None,
        alpha2: str = None,
        alpha3: str = None,
        numeric: int = None,
    ):
        cls = self._model_cls

        field_map = {
            "id": None,
            "alpha2": cls.alpha2,
            "alpha3": cls.alpha3,
            "numeric": cls.numeric,
        }

        model = None
        for arg, field in field_map.items():
            val = locals()[arg]
            if val is not None:
                model = cls.get_by_id(val) if arg == "id" else cls.get(field == val)

        return model.to_dto() if model is not None else None

    # def lookup(self, identifier, **kwargs) -> list[Country]:
    #     """Lookup a country by exact name."""
    #     if not identifier:
    #         return []

    #     identifier = self.ALIASES.get(identifier.lower(), identifier)
    #     identifier = normalize(identifier)

    #     rows = self._model_cls.fts_match(identifier, exact_match=True)
    #     return [r.dto for r in rows]

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
