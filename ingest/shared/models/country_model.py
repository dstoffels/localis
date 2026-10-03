from dataclasses import dataclass, field

from .model import Model
from .macroregion_model import MacroregionModel
from localis.utils.strings import normalize


@dataclass(slots=True)
class CountryModel(Model):
    alpha2: str
    alpha3: str | None
    geonames_id: int | None
    official_name: str | None
    common_name: str | None
    aliases: list[str]
    numeric: int | None
    flag: str | None
    historic: str | None
    # CLDR path, top-down (region, subregion)
    macroregions: list[MacroregionModel] = field(default_factory=list)
    groupings: list[MacroregionModel] = field(default_factory=list)

    LOOKUP_FIELDS = ("alpha2", "alpha3", "numeric")
    FILTER_FIELDS = {
        "name": ("name", "official_name", "common_name", "aliases"),
        "macroregion": ("macroregion_names", "macroregion_codes"),
    }
    CANON_FIELDS = ("name", "official_name", "common_name", "aliases")
    SHORT_NAMES = True

    def extract_lookup_values(self):
        """Historic entries reuse alpha2/alpha3/numeric across different withdrawn countries (e.g. CS: Czechoslovakia vs. Serbia and Montenegro, both numeric 891), so only the unique alpha_4 withdrawal code is a safe lookup key for them."""
        if self.historic:
            # only the unique alpha_4 withdrawal code is used for historic entries
            yield normalize(self.historic.split("|", 1)[0])
            return
        yield from Model.extract_lookup_values(self)

    @property
    def macroregion_names(self) -> list[str]:
        return [m.name for m in (*self.macroregions, *self.groupings)]

    @property
    def macroregion_codes(self) -> list[str]:
        return [m.code for m in (*self.macroregions, *self.groupings)]

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data["macroregions"] = "|".join(str(m.id) for m in self.macroregions)
        data["groupings"] = "|".join(str(m.id) for m in self.groupings)
        data.pop("id")
        return tuple(data.values())
