from dataclasses import dataclass
from typing import Literal
from .model import Model

MacroregionType = Literal["region", "subregion", "grouping"]


@dataclass(slots=True)
class MacroregionModel(Model):
    """A CLDR macroregion: a UN M49 region, a subregion within one, or a grouping of subregions."""

    code: str
    type: MacroregionType
    # a subregion's region, or the region a grouping's subregions all sit in; None for a region
    parent: "MacroregionModel | None"

    LOOKUP_FIELDS = ("code", "name")
    NUMERIC_LOOKUP = False

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["parent"] = self.parent.id if self.parent else None
        data.pop("id")
        return tuple(data.values())
