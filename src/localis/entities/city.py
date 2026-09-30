from dataclasses import dataclass
from .entity import Entity
from .country import CountryBase
from .subdivision import SubdivisionBase


@dataclass(slots=True)
class City(Entity):
    geonames_id: int
    admin1: SubdivisionBase | None
    admin2: SubdivisionBase | None
    country: CountryBase
    population: int
    lat: float
    lng: float
