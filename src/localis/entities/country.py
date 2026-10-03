from dataclasses import dataclass
from .entity import Entity
from .macroregion import MacroregionBase


@dataclass(slots=True)
class HistoricInfo:
    alpha_4: str
    withdrawal_date: str
    comment: str | None


@dataclass(slots=True)
class CountryBase(Entity):
    alpha2: str
    alpha3: str | None
    geonames_id: int | None


@dataclass(slots=True)
class Country(CountryBase):
    official_name: str | None
    common_name: str | None
    aliases: tuple[str, ...]
    numeric: int | None
    flag: str | None
    historic: HistoricInfo | None
    # CLDR path, top-down (region, subregion)
    macroregions: tuple[MacroregionBase, ...]
    groupings: tuple[MacroregionBase, ...]
