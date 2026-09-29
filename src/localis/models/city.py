from array import array
from pathlib import Path
from dataclasses import dataclass
from .model import DTO, Model, extract_base
from .country import CountryBase, CountryModel, CountryView
from .subdivision import SubdivisionBase, SubdivisionModel, SubdivisionView


@dataclass(slots=True)
class City(DTO):
    geonames_id: str
    admin1: SubdivisionBase
    admin2: SubdivisionBase
    country: CountryBase
    population: int
    lat: float
    lng: float


@dataclass(slots=True)
class CityModel(City, Model):
    LOOKUP_FIELDS = ("geonames_id",)
    FILTER_FIELDS = {
        "name": ("name",),
        "country": (
            "country.name",
            "country.alpha2",
            "country.alpha3",
        ),
        "subdivision": (
            "admin1.name",
            "admin1.iso_suffix",
            "admin1.iso_code",
            "admin1.geonames_code",
            "admin2.name",
            "admin2.iso_code",
            "admin2.geonames_code",
        ),
    }
    SEARCH_FIELDS = {
        "name": 1.0,
        "admin1.name": 0.6,
        "admin1.iso_suffix": 0.6,
        "country.name": 0.3,
        "country.alpha2": 0.3,
        "country.alpha3": 0.3,
    }

    admin1: SubdivisionModel | None
    admin2: SubdivisionModel | None
    country: CountryModel | None

    def to_dto(self) -> City:
        dto: City = extract_base(self, depth=1)
        dto.admin1 = self.admin1 and extract_base(self.admin1, depth=2)
        dto.admin2 = self.admin2 and extract_base(self.admin2, depth=2)
        dto.country = self.country and extract_base(self.country, depth=2)
        return dto

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["admin1"] = self.admin1.id if self.admin1 else None
        data["admin2"] = self.admin2.id if self.admin2 else None
        data["country"] = self.country.id if self.country else None
        data.pop("id")
        return tuple(data.values())

    @classmethod
    def from_row(
        cls,
        id: int,
        row: list[str | int | None],
        country_cache: dict[int, CountryModel],
        subdivision_cache: dict[int, SubdivisionModel],
        **kwargs,
    ) -> "CityModel":
        """Builds a CityModel instance from a raw data tuple (row) and injects country and subdivision models from their respective caches."""
        GEONAMES_ID_IDX = 1
        ADMIN1_IDX = 2
        ADMIN2_IDX = 3
        COUNTRY_IDX = 4
        POPULATION_IDX = 5
        LAT_IDX = 6
        LNG_IDX = 7

        row[GEONAMES_ID_IDX] = int(row[GEONAMES_ID_IDX])

        country_id = int(row[COUNTRY_IDX])
        row[COUNTRY_IDX] = country_cache.get(country_id)

        admin1_id = row[ADMIN1_IDX]
        if admin1_id:
            row[ADMIN1_IDX] = subdivision_cache.get(int(admin1_id))

        admin2_id = row[ADMIN2_IDX]
        if admin2_id:
            row[ADMIN2_IDX] = subdivision_cache.get(int(admin2_id))

        row[POPULATION_IDX] = int(row[POPULATION_IDX])
        row[LAT_IDX] = float(row[LAT_IDX])
        row[LNG_IDX] = float(row[LNG_IDX])

        return cls(id, *row)


class CityStore:
    """Columnar storage for all cities' field data, shared by every CityView."""

    __slots__ = (
        "names",
        "geonames_ids",
        "admin1_ids",
        "admin2_ids",
        "country_ids",
        "populations",
        "lats",
        "lngs",
    )

    def __init__(self):
        self.names: list[str] = []
        self.geonames_ids = array("I")
        self.admin1_ids = array("i")  # -1 sentinel for None
        self.admin2_ids = array("i")  # -1 sentinel for None
        self.country_ids = array("I")
        self.populations = array("I")
        self.lats = array("f")
        self.lngs = array("f")

    def append(
        self,
        name: str,
        geonames_id: int,
        admin1_id: int | None,
        admin2_id: int | None,
        country_id: int,
        population: int,
        lat: float,
        lng: float,
    ) -> None:
        self.names.append(name)
        self.geonames_ids.append(geonames_id)
        self.admin1_ids.append(admin1_id if admin1_id is not None else -1)
        self.admin2_ids.append(admin2_id if admin2_id is not None else -1)
        self.country_ids.append(country_id)
        self.populations.append(population)
        self.lats.append(lat)
        self.lngs.append(lng)

    def __len__(self) -> int:
        return len(self.names)


class CityView:
    """Lightweight runtime view over CityStore; used for Registry._cache instead of
    CityModel, which stays a plain mutable dataclass for ingestion. Each instance owns
    only its id, every field is read from the shared columnar store on access."""

    __slots__ = ("id", "_store", "_country_views", "_subdivision_views")

    SEARCH_FIELDS = CityModel.SEARCH_FIELDS

    def __init__(
        self,
        id: int,
        store: CityStore,
        country_views: dict[int, CountryView],
        subdivision_views: dict[int, SubdivisionView],
    ):
        self.id = id
        self._store = store
        self._country_views = country_views
        self._subdivision_views = subdivision_views

    @property
    def _idx(self) -> int:
        return self.id - 1

    @property
    def name(self) -> str:
        return self._store.names[self._idx]

    @property
    def geonames_id(self) -> int:
        return self._store.geonames_ids[self._idx]

    @property
    def admin1(self) -> SubdivisionView | None:
        aid = self._store.admin1_ids[self._idx]
        return self._subdivision_views.get(aid) if aid != -1 else None

    @property
    def admin2(self) -> SubdivisionView | None:
        aid = self._store.admin2_ids[self._idx]
        return self._subdivision_views.get(aid) if aid != -1 else None

    @property
    def country(self) -> CountryView | None:
        return self._country_views.get(self._store.country_ids[self._idx])

    @property
    def population(self) -> int:
        return self._store.populations[self._idx]

    @property
    def lat(self) -> float:
        return self._store.lats[self._idx]

    @property
    def lng(self) -> float:
        return self._store.lngs[self._idx]

    def get_search_values(self):
        for field_name, weight in self.SEARCH_FIELDS.items():
            obj = self
            value = None
            for nested in field_name.split("."):
                value = getattr(obj, nested, None)
                if value is None:
                    break
                obj = value
            if value is not None:
                yield (value, weight)

    def to_dto(self) -> City:
        admin1 = self.admin1
        admin2 = self.admin2
        country = self.country
        return City(
            id=self.id,
            name=self.name,
            geonames_id=self.geonames_id,
            admin1=(
                SubdivisionBase(
                    id=admin1.id,
                    name=admin1.name,
                    geonames_code=admin1.geonames_code,
                    iso_code=admin1.iso_code,
                    type=admin1.type,
                )
                if admin1
                else None
            ),
            admin2=(
                SubdivisionBase(
                    id=admin2.id,
                    name=admin2.name,
                    geonames_code=admin2.geonames_code,
                    iso_code=admin2.iso_code,
                    type=admin2.type,
                )
                if admin2
                else None
            ),
            country=(
                CountryBase(
                    id=country.id,
                    name=country.name,
                    alpha2=country.alpha2,
                    alpha3=country.alpha3,
                )
                if country
                else None
            ),
            population=self.population,
            lat=self.lat,
            lng=self.lng,
        )

    @classmethod
    def load(
        cls,
        filepath: Path,
        country_views: dict[int, CountryView],
        subdivision_views: dict[int, SubdivisionView],
    ) -> dict[int, "CityView"]:
        store = CityStore()
        views: dict[int, CityView] = {}
        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.rstrip("\r\n").split("\t")
                name, geonames_id_s, admin1_s, admin2_s, country_s, pop_s, lat_s, lng_s = row
                geonames_id = int(geonames_id_s)
                admin1_id = int(admin1_s) if admin1_s else None
                admin2_id = int(admin2_s) if admin2_s else None
                country_id = int(country_s)
                population = int(pop_s)
                lat = float(lat_s)
                lng = float(lng_s)
                store.append(
                    name,
                    geonames_id,
                    admin1_id,
                    admin2_id,
                    country_id,
                    population,
                    lat,
                    lng,
                )
                views[id] = cls(id, store, country_views, subdivision_views)
        return views
