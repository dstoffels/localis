from dataclasses import dataclass
from localis.entities.entity import Entity
from localis.entities.country import CountryBase


@dataclass(slots=True)
class SubdivisionBase(Entity):
    geonames_code: str | None
    geonames_id: int | None
    iso_code: str | None
    type: str
    admin_level: int


@dataclass(slots=True)
class Subdivision(SubdivisionBase):
    aliases: tuple[str, ...]
    parent: SubdivisionBase | None
    country: CountryBase
