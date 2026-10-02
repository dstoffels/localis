from dataclasses import dataclass
from .entity import Entity
from .country import CountryBase
from .subdivision import SubdivisionBase


@dataclass(slots=True)
class City(Entity):
    geonames_id: int
    subdivisions: list[SubdivisionBase]
    country: CountryBase
    population: int
    lat: float
    lng: float
