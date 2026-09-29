from array import array
from pathlib import Path
from dataclasses import dataclass
from localis.models.model import DTO, Model, extract_base
from localis.models import CountryBase, CountryModel, CountryView
from localis.utils import normalize
import hashlib


@dataclass(slots=True)
class SubdivisionBase(DTO):
    geonames_code: str | None
    iso_code: str | None
    type: str


@dataclass(slots=True)
class Subdivision(SubdivisionBase):
    aliases: list[str]
    admin_level: int
    parent: SubdivisionBase | None
    country: CountryBase


@dataclass(slots=True)
class SubdivisionModel(Subdivision, Model):
    LOOKUP_FIELDS = ("iso_code", "geonames_code")
    FILTER_FIELDS = {
        "name": ("name", "aliases"),
        "type": ("type",),
        "country": (
            "country.name",
            "country.alpha2",
            "country.alpha3",
            "country.numeric",
        ),
        "admin_level": ("admin_level",),
    }
    SEARCH_FIELDS = {
        "name": 1.0,
        "iso_suffix": 0.5,
        "aliases": 1.0,
        "parent.name": 0.4,
        "country.name": 0.4,
        "country.alpha2": 0.4,
        "country.alpha3": 0.4,
    }

    @property
    def iso_suffix(self) -> str:
        return self.iso_code.split("-")[1] if self.iso_code else ""

    parent: "SubdivisionModel"
    country: CountryModel

    def to_dto(self) -> Subdivision:
        dto: Subdivision = extract_base(self)
        dto.parent = self.parent and extract_base(self.parent, depth=2)
        dto.country = self.country and extract_base(self.country, depth=2)
        return dto

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["parent"] = self.parent.id if self.parent else None
        data["country"] = self.country.id
        data.pop("hashid", None)
        data["aliases"] = "|".join(self.aliases) if self.aliases else None
        data.pop("id")
        return tuple(data.values())

    @classmethod
    def from_row(
        cls,
        id: int,
        row: tuple[str | int | None],
        subdivision_cache: dict[int, "SubdivisionModel"],
        country_cache: dict[int, CountryModel],
        **kwargs,
    ) -> "SubdivisionModel":
        ALIAS_IDX = 4
        ADMIN_LEVEL_IDX = 5
        PARENT_IDX = 6
        COUNTRY_IDX = 7

        row[ALIAS_IDX] = [a for a in row[ALIAS_IDX].split("|") if a]
        row[ADMIN_LEVEL_IDX] = int(row[ADMIN_LEVEL_IDX])
        row[PARENT_IDX] = (
            subdivision_cache.get(int(row[PARENT_IDX]))
            if subdivision_cache and row[PARENT_IDX]
            else None
        )
        row[COUNTRY_IDX] = country_cache.get(int(row[COUNTRY_IDX]))

        return cls(id, *row)

    hashid: int | None = None

    def set_hashid(self) -> None:
        if not isinstance(self.country, int):
            key_parts = [
                self.country.alpha2,
                str(self.admin_level),
                normalize(self.name),
                self.iso_code
                or self.geonames_code,  # whichever is present at initialization
            ]
            key = "|".join(key_parts)
            # temporarily hash a unique id to later map admin2 subdivisions to their parents and to manually map ISO subdivisions that cannot be automatically merged with its geonames counterpart. hashid is ONLY used internally for these purposes during ingestion; once the subdvision data has been successfully merged, hashid is discarded.
            self.hashid = int.from_bytes(hashlib.md5(key.encode()).digest()[:8], "big")


class SubdivisionStore:
    """Columnar storage for all subdivisions' field data, shared by every SubdivisionView."""

    __slots__ = (
        "names",
        "geonames_codes",
        "iso_codes",
        "types",
        "aliases",
        "admin_levels",
        "parent_ids",
        "country_ids",
    )

    def __init__(self):
        self.names: list[str] = []
        self.geonames_codes: list[str] = []
        self.iso_codes: list[str] = []
        self.types: list[str] = []
        self.aliases: list[list[str]] = []
        self.admin_levels = array("B")
        self.parent_ids = array("i")  # -1 sentinel for None
        self.country_ids = array("I")

    def append(
        self,
        name: str,
        geonames_code: str,
        iso_code: str,
        type_: str,
        alias_list: list[str],
        admin_level: int,
        parent_id: int | None,
        country_id: int,
    ) -> None:
        self.names.append(name)
        self.geonames_codes.append(geonames_code)
        self.iso_codes.append(iso_code)
        self.types.append(type_)
        self.aliases.append(alias_list)
        self.admin_levels.append(admin_level)
        self.parent_ids.append(parent_id if parent_id is not None else -1)
        self.country_ids.append(country_id)

    def __len__(self) -> int:
        return len(self.names)


class SubdivisionView:
    """Lightweight runtime view over SubdivisionStore; used for Registry._cache instead of
    SubdivisionModel, which stays a plain mutable dataclass for ingestion. Cross-references
    (parent, country) are resolved lazily against already-fully-loaded view dicts, so load
    order never matters, unlike the ingestion-side object graph."""

    __slots__ = ("id", "_store", "_country_views", "_subdivision_views")

    SEARCH_FIELDS = SubdivisionModel.SEARCH_FIELDS

    def __init__(
        self,
        id: int,
        store: SubdivisionStore,
        country_views: dict[int, CountryView],
        subdivision_views: dict[int, "SubdivisionView"],
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
    def geonames_code(self) -> str:
        return self._store.geonames_codes[self._idx]

    @property
    def iso_code(self) -> str:
        return self._store.iso_codes[self._idx]

    @property
    def type(self) -> str:
        return self._store.types[self._idx]

    @property
    def aliases(self) -> list[str]:
        return self._store.aliases[self._idx]

    @property
    def admin_level(self) -> int:
        return self._store.admin_levels[self._idx]

    @property
    def parent(self) -> "SubdivisionView | None":
        pid = self._store.parent_ids[self._idx]
        return self._subdivision_views.get(pid) if pid != -1 else None

    @property
    def country(self) -> CountryView:
        return self._country_views.get(self._store.country_ids[self._idx])

    @property
    def iso_suffix(self) -> str:
        return self.iso_code.split("-")[1] if self.iso_code else ""

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

    def to_dto(self) -> Subdivision:
        parent = self.parent
        country = self.country
        return Subdivision(
            id=self.id,
            name=self.name,
            geonames_code=self.geonames_code,
            iso_code=self.iso_code,
            type=self.type,
            aliases=self.aliases,
            admin_level=self.admin_level,
            parent=(
                SubdivisionBase(
                    id=parent.id,
                    name=parent.name,
                    geonames_code=parent.geonames_code,
                    iso_code=parent.iso_code,
                    type=parent.type,
                )
                if parent
                else None
            ),
            country=CountryBase(
                id=country.id,
                name=country.name,
                alpha2=country.alpha2,
                alpha3=country.alpha3,
            ),
        )

    @classmethod
    def load(
        cls, filepath: Path, country_views: dict[int, CountryView]
    ) -> dict[int, "SubdivisionView"]:
        store = SubdivisionStore()
        views: dict[int, SubdivisionView] = {}
        with open(filepath, "r", encoding="utf-8") as f:
            for id, line in enumerate(f, start=1):
                row = line.rstrip("\r\n").split("\t")
                name, geonames_code, iso_code, type_, alias_s, admin_level_s, parent_s, country_s = row
                alias_list = [a for a in alias_s.split("|") if a]
                admin_level = int(admin_level_s)
                parent_id = int(parent_s) if parent_s else None
                country_id = int(country_s)
                store.append(
                    name,
                    geonames_code,
                    iso_code,
                    type_,
                    alias_list,
                    admin_level,
                    parent_id,
                    country_id,
                )
                views[id] = cls(id, store, country_views, views)
        return views
