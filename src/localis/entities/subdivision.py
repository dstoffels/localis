from .entity import Entity, entity
from .country import CountryBase


@entity
class SubdivisionBase(Entity):
    """A subdivision as other records nest it."""

    geonames_code: str | None
    geonames_id: int | None
    iso_code: str | None
    type: str | None
    admin_level: int

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by subdivisions.lookup(): the ISO code, or the GeoNames code of a subdivision ISO doesn't list."""
        # every subdivision comes from ISO, GeoNames or both
        key = self.iso_code or self.geonames_code
        if key is None:
            raise ValueError(f"subdivision {self.id} ({self.name}) has neither an ISO nor a GeoNames code")
        return key


@entity
class Subdivision(SubdivisionBase):
    """An ISO 3166-2 subdivision, a GeoNames one, or both merged."""

    aliases: list[str]
    parent: SubdivisionBase | None
    country: CountryBase
