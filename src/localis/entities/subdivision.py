from dataclasses import dataclass
from localis.entities.entity import Entity
from localis.entities.country import CountryBase


@dataclass(slots=True)
class SubdivisionBase(Entity):
    geonames_code: str | None
    geonames_id: int | None
    iso_code: str | None
    type: str | None
    admin_level: int

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by subdivisions.lookup(): the ISO code, or the GeoNames code of a subdivision ISO doesn't list."""
        key = self.iso_code or self.geonames_code
        # every subdivision comes from ISO, GeoNames or both
        assert key is not None
        return key


@dataclass(slots=True)
class Subdivision(SubdivisionBase):
    aliases: tuple[str, ...]
    parent: SubdivisionBase | None
    country: CountryBase
