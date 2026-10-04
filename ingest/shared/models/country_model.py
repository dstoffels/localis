from dataclasses import dataclass, field
from typing import Iterator

from .model import Model
from .macroregion_model import MacroregionModel
from .currency_model import CurrencyModel
from localis.utils.strings import normalize


@dataclass(slots=True)
class HistoricModel:
    """A country's ISO 3166-3 withdrawal, shipped as one "alpha_4|withdrawal_date|comment" cell."""

    alpha_4: str
    withdrawal_date: str
    comment: str | None

    def to_cell(self) -> str:
        return f"{self.alpha_4}|{self.withdrawal_date}|{self.comment or ''}"

    @classmethod
    def from_cell(cls, cell: str) -> "HistoricModel | None":
        if not cell:
            return None
        alpha_4, withdrawal_date, comment = cell.split("|", 2)
        return cls(alpha_4=alpha_4, withdrawal_date=withdrawal_date, comment=comment or None)


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
    historic: HistoricModel | None
    # CLDR path, top-down (region, subregion)
    macroregions: list[MacroregionModel] = field(default_factory=list)
    groupings: list[MacroregionModel] = field(default_factory=list)
    # legal tender in use, in CLDR's order
    currencies: list[CurrencyModel] = field(default_factory=list)

    LOOKUP_FIELDS = ("alpha2", "alpha3", "numeric")
    FILTER_FIELDS = {
        "name": ("name", "official_name", "common_name", "aliases"),
        "macroregion": ("macroregion_names", "macroregion_codes"),
        "currency": ("currency_names", "currency_codes"),
    }
    CANON_FIELDS = ("name", "official_name", "common_name", "aliases")
    SHORT_NAMES = True

    def extract_lookup_values(self) -> Iterator[str]:
        """Historic entries reuse alpha2/alpha3/numeric across different withdrawn countries (e.g. CS: Czechoslovakia vs. Serbia and Montenegro, both numeric 891), so only the unique alpha_4 withdrawal code is a safe lookup key for them."""
        if self.historic:
            yield normalize(self.historic.alpha_4)
            return
        yield from Model.extract_lookup_values(self)

    @property
    def macroregion_names(self) -> list[str]:
        return [m.name for m in (*self.macroregions, *self.groupings)]

    @property
    def macroregion_codes(self) -> list[str]:
        return [m.code for m in (*self.macroregions, *self.groupings)]

    @property
    def currency_names(self) -> list[str]:
        return [c.name for c in self.currencies]

    @property
    def currency_codes(self) -> list[str]:
        return [c.alpha3 for c in self.currencies]

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data["macroregions"] = "|".join(str(m.id) for m in self.macroregions)
        data["groupings"] = "|".join(str(m.id) for m in self.groupings)
        data["currencies"] = "|".join(str(c.id) for c in self.currencies)
        data["historic"] = self.historic.to_cell() if self.historic else None
        data.pop("id")
        return tuple(data.values())
