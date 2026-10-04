from dataclasses import dataclass, field
from typing import Literal
from .model import Model
from .script_model import ScriptModel

LanguageScope = Literal["individual", "macrolanguage", "special"]
LanguageType = Literal["living", "extinct", "historical", "constructed", "special"]
LanguageStatus = Literal["official", "regional", "de_facto"]


@dataclass(slots=True)
class LanguageScriptModel:
    """A script CLDR lists for a language; secondary when the language or the script isn't modern."""

    script: ScriptModel
    secondary: bool


@dataclass(slots=True)
class LanguageModel(Model):
    """An ISO 639-3 language."""

    alpha3: str
    alpha2: str | None
    bibliographic: str | None
    scope: LanguageScope
    type: LanguageType
    inverted_name: str | None
    # iso-codes' common name and CLDR's English names for the code, where they differ from ISO's
    aliases: list[str] = field(default_factory=list)
    # primary scripts first, then secondary, each in CLDR's order
    scripts: list[LanguageScriptModel] = field(default_factory=list)

    LOOKUP_FIELDS = ("alpha3", "alpha2", "bibliographic")
    FILTER_FIELDS = {
        "name": ("name", "inverted_name", "aliases"),
        "scope": ("scope",),
        "type": ("type",),
        "script": ("script_values",),
    }
    CANON_FIELDS = ("name", "inverted_name", "aliases")
    SHORT_NAMES = True

    @property
    def script_values(self) -> list[str]:
        return [v for s in self.scripts for v in (s.script.alpha4, s.script.name, *s.script.aliases)]

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data["scripts"] = "|".join(str(s.script.id) for s in self.scripts if not s.secondary)
        data["secondary_scripts"] = "|".join(str(s.script.id) for s in self.scripts if s.secondary)
        data.pop("id")
        return tuple(data.values())


@dataclass(slots=True)
class CountryLanguageModel:
    """A language CLDR gives a country an official status for, in the script its tag names; shipped as one "language_id:status:population_percent:script_id" item."""

    language: LanguageModel
    status: LanguageStatus
    population_percent: float | None
    script: ScriptModel | None

    def to_cell(self) -> str:
        percent = "" if self.population_percent is None else repr(self.population_percent)
        return f"{self.language.id}:{self.status}:{percent}:{self.script.id if self.script else ''}"
