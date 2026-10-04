from dataclasses import dataclass
from typing import Literal
from .entity import Entity
from .script import LanguageScript, ScriptBase

LanguageScope = Literal["individual", "macrolanguage", "special"]
LanguageType = Literal["living", "extinct", "historical", "constructed", "special"]
LanguageStatus = Literal["official", "regional", "de_facto"]


@dataclass(slots=True)
class LanguageBase(Entity):
    alpha3: str
    alpha2: str | None

    @property
    def key(self) -> str:
        """The stable reference to store instead of id, resolved by languages.lookup(): the ISO 639-3 alpha3."""
        return self.alpha3


@dataclass(slots=True)
class Language(LanguageBase):
    bibliographic: str | None
    scope: LanguageScope
    type: LanguageType
    inverted_name: str | None
    aliases: tuple[str, ...]
    # primary scripts first, then secondary, each in CLDR's order
    scripts: tuple[LanguageScript, ...]


@dataclass(slots=True)
class CountryLanguage(LanguageBase):
    status: LanguageStatus
    # CLDR's share of the country's population; shares overlap, since people speak several languages
    population_percent: float | None
    # the script CLDR states the status for; None where its tag names none
    script: ScriptBase | None
