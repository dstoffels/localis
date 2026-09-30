from dataclasses import dataclass
from .model import Model
from .country_model import CountryModel
from localis.utils.strings import normalize
import hashlib


@dataclass(slots=True)
class SubdivisionModel(Model):
    iso_code: str | None
    geonames_code: str | None
    geonames_id: int | None
    type: str
    aliases: list[str]
    admin_level: int
    parent: "SubdivisionModel | None"
    country: CountryModel
    hashid: int | None = None

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
        ALIAS_IDX = 5
        ADMIN_LEVEL_IDX = 6
        PARENT_IDX = 7
        COUNTRY_IDX = 8

        row[ALIAS_IDX] = [a for a in row[ALIAS_IDX].split("|") if a]
        row[ADMIN_LEVEL_IDX] = int(row[ADMIN_LEVEL_IDX])
        row[PARENT_IDX] = (
            subdivision_cache.get(int(row[PARENT_IDX]))
            if subdivision_cache and row[PARENT_IDX]
            else None
        )
        row[COUNTRY_IDX] = country_cache.get(int(row[COUNTRY_IDX]))

        return cls(id, *row)

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
