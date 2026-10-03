from dataclasses import dataclass
from typing import Literal
from .model import Model

MacroregionType = Literal["region", "subregion", "grouping"]


@dataclass(slots=True)
class MacroregionModel(Model):
    """A CLDR macroregion: a UN M49 region, a subregion within one, or a grouping of subregions or countries."""

    code: str
    type: MacroregionType
    # a subregion's region, or the region CLDR files a grouping under; None for a region and the groupings filed under World
    parent: "MacroregionModel | None"

    LOOKUP_FIELDS = ("code", "name")
    NUMERIC_LOOKUP = False

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["parent"] = self.parent.id if self.parent else None
        data.pop("id")
        return tuple(data.values())
