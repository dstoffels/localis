from typing import Literal
from .entity import Entity, entity

MacroregionType = Literal["region", "subregion", "grouping"]


@entity
class MacroregionBase(Entity):
    """A macroregion as other records nest it."""

    code: str
    type: MacroregionType

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by macroregions.lookup(): the CLDR code."""
        return self.code


@entity
class Macroregion(MacroregionBase):
    """A CLDR macroregion: a UN M49 region, a subregion within one, or a grouping."""

    # a subregion's region, or the region CLDR files a grouping under; None for a region and the groupings filed under World
    parent: MacroregionBase | None
