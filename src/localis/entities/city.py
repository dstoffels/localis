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

    @property
    def key(self) -> int:
        """The stable reference to store instead of id, resolved by cities.lookup(): the GeoNames ID."""
        return self.geonames_id
