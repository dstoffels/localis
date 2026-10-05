from dataclasses import dataclass
from .entity import Entity, entity
from .macroregion import MacroregionBase
from .currency import CurrencyBase
from .language import CountryLanguage


@dataclass(slots=True)
class HistoricInfo:
    """A country's ISO 3166-3 withdrawal."""

    alpha_4: str
    withdrawal_date: str
    comment: str | None


@entity
class CountryBase(Entity):
    """A country as other records nest it."""

    alpha2: str
    alpha3: str | None
    geonames_id: int | None

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by countries.lookup(); a nested country is always a current one, so its alpha2."""
        return self.alpha2


@entity
class Country(CountryBase):
    """An ISO 3166-1 country, or an ISO 3166-3 withdrawn one."""

    official_name: str | None
    common_name: str | None
    aliases: list[str]
    numeric: int | None
    flag: str | None
    historic: HistoricInfo | None
    # CLDR path, top-down (region, subregion)
    macroregions: list[MacroregionBase]
    groupings: list[MacroregionBase]
    # legal tender in use, in CLDR's order; none for historic entries
    currencies: list[CurrencyBase]
    # one per CLDR tag with an official status, by population share; none for historic entries
    languages: list[CountryLanguage]

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by countries.lookup(): alpha2, or a historic entry's alpha_4, since ISO reused historic alpha2s."""
        return self.historic.alpha_4 if self.historic else self.alpha2
