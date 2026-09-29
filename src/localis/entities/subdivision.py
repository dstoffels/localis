from dataclasses import dataclass
from localis.entities.entity import Entity
from localis.entities.country import CountryBase


@dataclass(slots=True)
class SubdivisionBase(Entity):
    geonames_code: str | None
    iso_code: str | None
    type: str


@dataclass(slots=True)
class Subdivision(SubdivisionBase):
    aliases: list[str]
    admin_level: int
    parent: SubdivisionBase | None
    country: CountryBase
