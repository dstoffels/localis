from .entity import Entity, entity
from .country import CountryBase
from .subdivision import SubdivisionBase


@entity
class City(Entity):
    """A GeoNames populated place from cities500."""

    geonames_id: int
    # the full chain, ascending admin_level
    subdivisions: list[SubdivisionBase]
    country: CountryBase
    population: int
    lat: float
    lng: float

    @property
    def key(self) -> int:
        """The stable reference to store instead of id, resolved by cities.lookup(): the GeoNames ID."""
        return self.geonames_id
