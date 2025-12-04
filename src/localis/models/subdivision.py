from dataclasses import dataclass
from localis.models.model import DTO, Model, extract_base
from localis.models import CountryBase, CountryModel
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

    @property
    def dto(self):
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
        country_cache: dict[int, CountryModel],
    ) -> "SubdivisionModel":
        COUNTRY_IDX = 7
        ALIAS_IDX = 4
        row[ALIAS_IDX] = row[ALIAS_IDX].split("|")

        row[COUNTRY_IDX] = country_cache.get(int(row[COUNTRY_IDX]))
        return cls(id, *row)

    # temporarily hash a unique id to later map admin2 subdivisions to their parents and to manually map ISO subdivisions that cannot be automatically merged with its geonames counterpart. hashid is ONLY used internally for these purposes; once the subdvision data has been successfully merged, hashid is discarded.
    hashid: int = None

    def __post_init__(self):
        if not isinstance(self.country, int):
            key_parts = [
                self.country.alpha2,
                str(self.admin_level),
                normalize(self.name),
                self.iso_code
                or self.geonames_code,  # whichever is present at initialization
            ]
            key = "|".join(key_parts)
            self.hashid = int.from_bytes(hashlib.md5(key.encode()).digest()[:8], "big")

    # @property
    # def search_context(self) -> str:
    #     return " ".join(
    #         [
    #             self.name,
    #             self.iso_suffix,
    #             self.type or "",
    #             self.country.alpha2 if self.country else "",
    #             self.country.alpha3 if self.country else "",
    #             self.country.name if self.country else "",
    #         ],
    #     ).lower()
