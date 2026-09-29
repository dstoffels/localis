from dataclasses import dataclass
from .entity import Entity
from .country import CountryBase
from .subdivision import SubdivisionBase


@dataclass(slots=True)
class City(Entity):
    geonames_id: str
    admin1: SubdivisionBase
    admin2: SubdivisionBase
    country: CountryBase
    population: int
    lat: float
    lng: float
