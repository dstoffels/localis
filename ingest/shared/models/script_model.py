from dataclasses import dataclass, field
from .model import Model


@dataclass(slots=True)
class ScriptModel(Model):
    """An ISO 15924 script code."""

    alpha4: str
    numeric: int | None
    # CLDR's English names for the code, where they differ from ISO's
    aliases: list[str] = field(default_factory=list)

    LOOKUP_FIELDS = ("alpha4", "numeric")
    FILTER_FIELDS = {"name": ("name", "aliases")}
    CANON_FIELDS = ("name", "aliases")
    SHORT_NAMES = True

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data.pop("id")
        return tuple(data.values())
