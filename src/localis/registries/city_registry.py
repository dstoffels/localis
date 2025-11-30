from localis.data import CityModel
from localis.registries import Registry, CountryRegistry, SubdivisionRegistry
from localis.index.filter_index import FilterIndex
from collections import defaultdict


class CityRegistry(Registry[CityModel]):
    DATAFILE = "cities.tsv"
    MODEL_CLS = CityModel

    def __init__(
        self, countries: CountryRegistry, subdivisions: SubdivisionRegistry, **kwargs
    ):
        self._countries = countries
        self._subdivisions = subdivisions
        super().__init__(**kwargs)

    def _parse_row(self, id: int, row: list[str]):
        name, admin1_id, admin2_id, country_id, population, lat, lng, search_tokens = (
            row
        )
        admin1 = self._subdivisions.cache.get(int(admin1_id)) if admin1_id else None
        admin2 = self._subdivisions.cache.get(int(admin2_id)) if admin2_id else None
        country = self._countries.cache.get(int(country_id)) if country_id else None

        city = CityModel(
            id=id,
            name=name,
            admin1=admin1,
            admin2=admin2,
            country=country,
            population=int(population),
            lat=float(lat),
            lng=float(lng),
        )
        city.search_tokens = search_tokens
        self._cache[id] = city

    def get(self, identifier) -> CityModel | None:
        """Get a city by its id"""
        return super().get(identifier)

    def load_filters(self):
        self._filter_index = FilterIndex(
            cache=self.cache, filter_fields=self.MODEL_CLS.FILTER_FIELDS
        )

    def filter(
        self,
        *,
        name=None,
        limit: int = None,
        subdivision: str = None,
        country: str = None,
        population__lt: int = None,
        population__gt: int = None,
        **kwargs,
    ):
        """Filter cities by name, subdivision or country with additional filtering by population. Multiple filters use logical AND."""
        kwargs = {
            "subdivision": subdivision,
            "country": country,
        }
        results = super().filter(name=name, limit=limit, **kwargs)
        # if population__gt is not None or population__lt is not None:
        #     results.sort()
        return results

    def search(self, query, limit=None, population_sort: bool = False, **kwargs):
        """Search cities by name, subdivision, or country. Can optionally sort by population, which is great for autocompletes."""
        results = super().search(query=query, limit=None, **kwargs)
        if population_sort:
            results.sort(key=lambda x: x[0].population, reverse=True)
        return results[:limit]


# ----------- SINGLETON ----------- #
from localis.registries.country_registry import countries
from localis.registries.subdivision_registry import subdivisions

cities: CityRegistry = CityRegistry(countries=countries, subdivisions=subdivisions)


#     ID_FIELDS = ("id", "geonames_id")

#     SEARCH_FIELD_WEIGHTS = {
#         "name": 1.0,
#         "alt_names": 1.5,
#         "admin1": 0.2,
#         "admin2": 0.1,
#         "country": 0.2,
#     }

#     SEARCH_ORDER_FIELDS = ["population"]

#     META_URL_KEY = "cities_tsv_url"

#     def __init__(self, model_cls):
#         super().__init__(model_cls)
#         self._order_by = "population DESC"

#         self._meta = MetaStore()
#         self._loaded = False
#         """WARNING: Do not mutate directly, controlled by set_loaded()"""
#         self.set_loaded()

#     def set_loaded(self) -> bool:
#         self._loaded = db.CONFIG_FILE.exists()

#     def load(self, confirmed: bool = False, custom_dir: str = "") -> None:
#         if self._loaded:
#             print("Cities data already loaded.")
#             return

#         # USER CONFIRMATION
#         confirmed = confirmed or input(
#             "Loading cities is HEAVY, there are nearly half a million entries and it expands the database to ~250MB. Proceeding with load will copy the sqlite database to your project root, download cities.tsv, load it into the copied database and update your .gitignore. Are you sure you want to proceed? [y/N] "
#         ).lower() in ["y", "yes"]

#         # DID NOT CONFIRM
#         if not confirmed:
#             print("Aborting load.")
#             return

#         # COPY DATABASE
#         print(f"Copying database to {custom_dir}/{db.FILENAME}...")
#         path = db.copy_to(custom_dir)
#         db.set_db_path(path)

#         # UPDATE GITIGNORE
#         print(f"Updating .gitignore...")

#         gitignore_path = ".gitignore"
#         gitignore_lines = f"{db.FILENAME}\n.localis.conf\n"

#         if os.path.exists(gitignore_path):
#             with open(gitignore_path, "r") as f:
#                 existing_content = f.read()
#                 if gitignore_lines in existing_content:
#                     print(".gitignore already updated. Skipping...")
#         else:
#             existing_content = ""

#         with open(gitignore_path, "a") as f:
#             if existing_content and not existing_content.endswith("\n"):
#                 f.write("\n")
#             f.write(gitignore_lines)

#         # DOWNLOAD TSV FIXTURE
#         url = self._meta.get(self.META_URL_KEY)
#         if url:
#             print("Downloading TSV fixture...")

#             try:
#                 response = requests.get(url)
#                 response.raise_for_status()  # just to be safe
#             except requests.HTTPError as e:
#                 if e.response.status_code == 404:
#                     e.add_note(
#                         f"There is a problem with the cities.tsv url, please raise a new issue: https://github.com/dstoffels/localis/issues.\nurl: {url}"
#                     )
#                 raise e

#             # LOAD TSV INTO DATABASE
#             print("TSV fixture downloaded, loading cities into database...")
#             tsv = io.StringIO(response.text)
#             CityModel.load(tsv)

#             self.set_loaded()
#             print(f"{self.count} cities loaded.")
#             print(
#                 "Run 'localis unload cities' in the CLI or 'localis.cities.unload()' to revert."
#             )

#         else:
#             raise ValueError(
#                 f"Error fetching the cities fixture url, the database (meta table) may have been corrupted. Please submit a new issue: https://github.com/dstoffels/localis/issues.\nCurrent url: {url}"
#             )

#     def unload(self) -> None:
#         if not self._loaded:
#             print("No cities to unload.")
#         else:
#             # UNLOAD FILES
#             print(f"Removing database and localis.conf...")
#             db.revert_to_default()
#             print("Files removed.")

#             # UPDATE GITIGNORE
#             gitignore_lines = f"{db.FILENAME}\n.localis.conf\n"

#             print("Updating .gitignore...")
#             with open(".gitignore", "r+") as f:
#                 content = f.read()
#                 content = content.replace(gitignore_lines, "")
#                 f.seek(0)
#                 f.write(content)
#                 f.truncate()

#             self.set_loaded()
#             self._count = None
#             print("Cities successfully unloaded from db.")

#     @property
#     def count(self):
#         self._check_loaded()
#         return super().count

#     def _check_loaded(self):
#         if not self._loaded:
#             raise RuntimeError(
#                 "Cities data not yet loaded. Load with `localis.cities.load()` or `localis load cities` from the CLI."
#             )

#     def get(self, *, id: int = None, geonames_id: str = None, **kwargs):
#         self._check_loaded()
#         cls = self._model_cls

#         field_map = {
#             "id": None,
#             "geonames_id": cls.geonames_id,
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
#         admin1: str = None,
#         admin2: str = None,
#         country: str = None,
#         alt_name: str = None,
#         **kwargs,
#     ):
#         self._check_loaded()
#         if kwargs:
#             return []
#         if admin1:
#             kwargs["admin1"] = admin1
#         if admin2:
#             kwargs["admin2"] = admin2
#         if country:
#             kwargs["country"] = country
#         if alt_name:
#             kwargs["alt_names"] = alt_name

#         return super().filter(query, name, limit, **kwargs)

#     def search(self, query, limit=None, **kwargs):
#         self._check_loaded()
#         return super().search(query, limit, **kwargs)

#     def for_country(
#         self,
#         *,
#         id: int = None,
#         alpha2: str = None,
#         alpha3: str = None,
#         numeric: int = None,
#         population__lt: int | None = None,
#         population__gt: int | None = None,
#         **kwargs,
#     ) -> list[City]:
#         self._check_loaded()
#         if population__gt is not None and population__lt is not None:
#             raise ValueError("population__gt and population__lt are mutually exclusive")

#         provided = {
#             k: v
#             for k, v in locals().items()
#             if k in localis.countries.ID_FIELDS and v is not None
#         }
#         country = localis.countries.get(**provided)
#         if country is None:
#             return []

#         country_field = "|".join([country.name, country.alpha2, country.alpha3])
#         results: list[CityModel] = self._model_cls.select(
#             CityModel.country == country_field
#         )

#         dtos = [r.to_dto() for r in results]
#         if population__gt is not None:
#             return [d for d in dtos if d.population > population__gt]
#         elif population__lt is not None:
#             return [d for d in dtos if d.population < population__lt]
#         else:
#             return dtos

#     def for_subdivision(
#         self,
#         *,
#         id: int = None,
#         geonames_code: str = None,
#         iso_code: str = None,
#         population__lt: int | None = None,
#         population__gt: int | None = None,
#         **kwargs,
#     ) -> list[City]:
#         self._check_loaded()
#         if population__gt is not None and population__lt is not None:
#             raise ValueError("population__gt and population__lt are mutually exclusive")

#         provided = {
#             k: v
#             for k, v in locals().items()
#             if k in localis.subdivisions.ID_FIELDS and v is not None
#         }

#         sub = localis.subdivisions.get(**provided)

#         if sub is None:
#             return []

#         sub_field = "|".join([sub.name, sub.geonames_code or "", sub.iso_code or ""])
#         expr = CityModel.admin1 == sub_field
#         if population__lt:
#             expr = expr & (CityModel.population < pad_num_w_zeros(population__lt))
#         elif population__gt:
#             expr = expr & (CityModel.population > pad_num_w_zeros(population__gt))
#         results: list[CityModel] = self._model_cls.select(expr)

#         if not results:
#             results = self._model_cls.select(CityModel.admin2 == sub_field)

#         dtos = [
#             r.to_dto()
#             for r in results
#             if r.admin1 == sub_field or r.admin2 == sub_field
#         ]

#         if population__gt is not None:
#             return [d for d in dtos if d.population > population__gt]
#         elif population__lt is not None:
#             return [d for d in dtos if d.population < population__lt]
#         else:
#             return dtos
