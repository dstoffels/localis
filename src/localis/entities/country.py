from dataclasses import dataclass
from .entity import Entity


@dataclass(slots=True)
class CountryBase(Entity):
    alpha2: str
    alpha3: str | None


@dataclass(slots=True)
class Country(CountryBase):
    official_name: str
    aliases: list[str]
    numeric: int | None
    flag: str | None
