from localis.data import CountryModel
from localis.registries import Registry
from localis.index import FilterIndex


class CountryRegistry(Registry[CountryModel]):
    DATAFILE = "countries.tsv"
    MODEL_CLS = CountryModel

    def _parse_row(self, id: int, row: list[str]):
        if id == 0:
            return

        name, official_name, aliases, alpha2, alpha3, numeric, flag, search_tokens = row

        country = CountryModel(
            id=id,
            name=name,
            official_name=official_name,
            aliases=[alt for alt in aliases.split("|") if alt],
            alpha2=alpha2,
            alpha3=alpha3,
            numeric=numeric,
            flag=flag,
        )

        country.search_tokens = search_tokens
        self._cache[id] = country

    def get(self, identifier: str | int) -> CountryModel | None:
        """Get a country by its alpha2, alpha3, numeric code, or id."""
        return super().get(identifier)

    def load_filters(self):
        self._filter_index = FilterIndex(
            cache=self.cache, filter_fields=self.MODEL_CLS.FILTER_FIELDS
        )

    def filter(self, *, name: str = None, limit: int = None, **kwargs):
        """Filter countries by any of its names (name, official_name, or aliases)."""
        return super().filter(name=name, limit=limit, **kwargs)

    def search(self, query, limit=None) -> list[tuple[CountryModel, float]]:
        return super().search(query, limit)


countries = CountryRegistry()

# class CountryRegistry(Registry[CountryModel, Country]):
#     """
#     Registry for managing Country entities.

#     Supports get by alpha2, alpha3 & numeric codes, lookup by country name with support for some aliases/former names,
#     and fuzzy search.
#     """

#     ID_FIELDS = ("id", "alpha2", "alpha3", "numeric")

#     SEARCH_FIELD_WEIGHTS = {
#         "name": 1.0,
#         "official_name": 1.0,
#         "alt_names": 1.0,
#     }

#     def get(
#         self,
#         *,
#         id: int = None,
#         alpha2: str = None,
#         alpha3: str = None,
#         numeric: int = None,
#         **kwargs,
#     ):
#         cls = self._model_cls

#         field_map = {
#             "id": None,
#             "alpha2": cls.alpha2,
#             "alpha3": cls.alpha3,
#             "numeric": cls.numeric,
#         }

#         model = None
#         for arg, field in field_map.items():
#             val = locals()[arg]
#             if val is not None:
#                 model = cls.get_by_id(val) if arg == "id" else cls.get(field == val)

#         return model.to_dto() if model is not None else None

#     def filter(
#         self,
#         query=None,
#         name=None,
#         limit=None,
#         official_name: str = None,
#         alt_name: str = None,
#         **kwargs,
#     ):
#         if kwargs:
#             return []
#         if official_name:
#             kwargs["official_name"] = official_name
#         if alt_name:
#             kwargs["alt_names"] = alt_name

#         return super().filter(query, name, limit, **kwargs)

#     @property
#     def _sql_filter_base(self):
#         return f"""SELECT c.*, f.tokens FROM countries_fts f
#         JOIN countries c ON f.rowid = c.id
#         """
