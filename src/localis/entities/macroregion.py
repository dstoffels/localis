from dataclasses import dataclass
from typing import Literal
from .entity import Entity

MacroregionType = Literal["region", "subregion", "grouping"]


@dataclass(slots=True)
class MacroregionBase(Entity):
    code: str
    type: MacroregionType


@dataclass(slots=True)
class Macroregion(MacroregionBase):
    # a subregion's region, or the region CLDR files a grouping under; None for a region and the groupings filed under World
    parent: MacroregionBase | None
