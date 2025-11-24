from localis.data import Subdivision, Country
from localis.registries import Registry, CountryRegistry
import csv
from localis.index import FilterIndex


class SubdivisionRegistry(Registry[Subdivision]):
    DATAFILE = "subdivisions.tsv"

    def __init__(self, countries: CountryRegistry, **kwargs):
        self._countries = countries
        super().__init__(**kwargs)

    def load(self):
        # need to sort the subdivision rows before parsing so the parent subdivisions are already cached when their children need to reference them.
        self._cache = {}
        sub_groups: list[tuple[int, list[str]]] = []

        with open(self.DATA_PATH / self.DATAFILE, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="\t")
            headers = next(reader)
            for id, row in enumerate(reader, 1):
                sub_groups.append((id, row))

        sub_groups.sort(key=lambda r: r[1][5])

        for id, row in sub_groups:
            self._parse_row(id, row)

    def _parse_row(self, id: int, row: list[str]):
        self.cache[id] = Subdivision(
            id=id,
            name=row[0],
            alt_names=[alt for alt in row[1].split("|") if alt],
            geonames_code=row[2] or None,
            iso_code=row[3] or None,
            type=row[4] or None,
            admin_level=1 if row[5] is None else 2,
            parent=self.cache.get(int(row[5])) if row[5] else None,
            country=self._countries.cache.get(int(row[6])),
        )

    def load_lookups(self):
        self._lookup_index = {}
        for sub in self.cache.values():
            if sub.geonames_code:
                self._lookup_index[sub.geonames_code] = sub

            if sub.iso_code:
                self._lookup_index[sub.iso_code] = sub

    def get(
        self, *, id=None, geonames_code: str = None, iso_code: str = None, **kwargs
    ):
        kwargs = {
            "geonames_code": geonames_code,
            "iso_code": iso_code,
        }
        return super().get(id=id, **kwargs)

    def load_filters(self):
        self._filter_index = FilterIndex()

        # Pre-build the index dict structure, then bulk assign
        from collections import defaultdict

        index = defaultdict(lambda: defaultdict(set))
        subs = self.cache.values()

        for sub in subs:
            sub_id = sub.id
            country = sub.country  # Single access

            # Direct dict assignments (faster than method calls)
            index["name"][sub.name].add(sub_id)
            index["type"][sub.type].add(sub_id)
            index["admin_level"][sub.admin_level].add(sub_id)
            index["country"][country.name].add(sub_id)
            index["country"][country.alpha2].add(sub_id)
            index["country"][country.alpha3].add(sub_id)

        self._filter_index.index = index

    def filter(
        self,
        *,
        name: str = None,
        type: str = None,
        admin_level: int = None,
        country: str = None,
        **kwargs,
    ):
        kwargs = {
            "type": type,
            "admin_level": admin_level,
            "country": country,
        }

        return super().filter(name=name, **kwargs)


# class SubdivisionRegistry(Registry[SubdivisionModel, Subdivision]):
#     """
#     Registry for managing Subdivision entities.

#     Supports exact lookup by ISO code, alpha2, or country code,
#     fuzzy search by these keys, and filtering by country or country code.
#     """

#     ID_FIELDS = ("id", "geonames_code", "iso_code")

#     SEARCH_FIELD_WEIGHTS = {"name": 1.0, "alt_names": 0.4, "country": 0.33}

#     def get(
#         self,
#         *,
#         id: int = None,
#         iso_code: str = None,
#         geonames_code: str = None,
#         **kwargs
#     ):
#         cls = self._model_cls

#         field_map = {
#             "id": None,
#             "iso_code": cls.iso_code,
#             "geonames_code": cls.geonames_code,
#         }

#         model = None
#         for arg, field in field_map.items():
#             val = locals()[arg]
#             if val is not None:
#                 model = cls.get_by_id(val) if arg == "id" else cls.get(field == val)

#         return model.to_dto() if model is not None else None

#     def filter(
#         self,
#         query: str = None,
#         name: str = None,
#         limit: int = None,
#         type: str = None,
#         country: str = None,
#         alt_name: str = None,
#         **kwargs
#     ):
#         if kwargs:
#             return []
#         if type is not None:
#             kwargs["type"] = type
#         if country is not None:
#             kwargs["country"] = country
#         if alt_name is not None:
#             kwargs["alt_names"] = alt_name

#         return super().filter(query, name, limit, **kwargs)

#     def for_country(
#         self,
#         *,
#         admin_level: int | None = 1,
#         id: int = None,
#         alpha2: str = None,
#         alpha3: str = None,
#         numeric: int = None,
#         **kwargs
#     ) -> list[Subdivision]:
#         """Get all subdivisions for a given country by id, alpha2, alpha3 or numeric code. Can filter results by admin_level (default=1)."""
#         provided = {
#             k: v
#             for k, v in locals().items()
#             if k in ("id", "alpha2", "alpha3", "numeric") and v is not None
#         }
#         country = localis.countries.get(**provided)
#         if country is None:
#             return []

#         country_field = "|".join([country.name, country.alpha2, country.alpha3])
#         results: list[SubdivisionModel] = self._model_cls.select(
#             SubdivisionModel.country == country_field
#         )

#         dtos = [r.to_dto() for r in results]

#         return [d for d in dtos if d.admin_level == admin_level or admin_level == None]

#     def types_for_country(
#         self,
#         *,
#         admin_level: int | None = 1,
#         id: int = None,
#         alpha2: str = None,
#         alpha3: str = None,
#         numeric: int = None,
#         **kwargs
#     ) -> list[str]:
#         """Fetch a list of distinct subdivision types for a given country by id, alpha2, alpha3 or numeric code. Can filter results by admin level (default=1)"""
#         provided = {
#             k: v
#             for k, v in locals().items()
#             if k in localis.countries.ID_FIELDS and v is not None
#         }
#         results = self.for_country(admin_level=admin_level, **provided)

#         types = set(
#             [
#                 r.type
#                 for r in results
#                 if r.type is not None and r.admin_level == admin_level
#             ]
#         )

#         return list(types)
