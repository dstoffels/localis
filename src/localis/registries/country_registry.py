from localis.data import Country
from localis.registries import Registry
from localis.index import FilterIndex


class CountryRegistry(Registry[Country]):
    DATAFILE = "countries.tsv"

    def _parse_row(self, id: int, row: list[str]):
        if id == 0:
            return

        self.cache[id] = Country(
            id=id,
            name=row[0],
            official_name=row[1],
            alt_names=[alt for alt in row[2].split("|") if alt],
            alpha2=row[3],
            alpha3=row[4],
            numeric=int(row[5]),
            flag=row[6],
        )

    def load_lookups(self):
        self._lookup_index = {}
        for c in self.cache.values():
            self._lookup_index[c.alpha2] = c
            self._lookup_index[c.alpha3] = c
            self._lookup_index[c.numeric] = c

    def get(
        self,
        *,
        id: int = None,
        alpha2: str = None,
        alpha3: str = None,
        numeric: int = None,
        **kwargs,
    ):
        kwargs = {
            "alpha2": alpha2,
            "alpha3": alpha3,
            "numeric": numeric,
        }
        return super().get(id=id, **kwargs)

    def load_filters(self):
        self._filter_index = FilterIndex()
        for country in self.cache.values():
            self._filter_index.add("name", country.name, country.id)
            if country.official_name:
                self._filter_index.add("name", country.official_name, country.id)
            for alt in country.alt_names:
                self._filter_index.add("name", alt, country.id)

    def filter(self, *, name=None, **kwargs):
        return super().filter(name=name, **kwargs)


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
