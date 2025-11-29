from dataclasses import dataclass
from .model import DTO, Model
from sys import intern


@dataclass(slots=True)
class CountryBase(DTO):
    alpha2: str
    alpha3: str


@dataclass(slots=True)
class Country(CountryBase):
    official_name: str
    aliases: list[str]
    numeric: int
    flag: str


@dataclass(slots=True)
class CountryModel(Country, Model):

    def set_search_meta(self):
        self.search_fields = (
            self.name.lower(),
            self.official_name.lower(),
            self.alpha2.lower(),
            self.alpha3.lower(),
            *(a.lower() for a in self.aliases),
        )

        self.search_context = " ".join(self.search_fields)
