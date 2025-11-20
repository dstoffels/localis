from villager.registries.registry import Registry
from villager.data import CountryModel, Country


class CountryRegistry(Registry[CountryModel, Country]):
    """
    Registry for managing Country entities.

    Supports get by alpha2, alpha3 & numeric codes, lookup by country name with support for some aliases/former names,
    and fuzzy search.
    """

    ID_FIELDS = ("id", "alpha2", "alpha3", "numeric")

    SEARCH_FIELD_WEIGHTS = {
        "name": 1.0,
        "official_name": 1.0,
        "alt_names": 1.0,
    }

    def get(
        self,
        *,
        id: int = None,
        alpha2: str = None,
        alpha3: str = None,
        numeric: int = None,
        **kwargs,
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

    def filter(
        self,
        query=None,
        name=None,
        limit=None,
        official_name: str = None,
        alt_name: str = None,
        **kwargs,
    ):
        if kwargs:
            return []
        if official_name:
            kwargs["official_name"] = official_name
        if alt_name:
            kwargs["alt_names"] = alt_name

        return super().filter(query, name, limit, **kwargs)

    @property
    def _sql_filter_base(self):
        return f"""SELECT c.*, f.tokens FROM countries_fts f
        JOIN countries c ON f.rowid = c.id
        """
