from dataclasses import dataclass
from .model import DTO, Model


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
    LOOKUP_FIELDS = ("alpha2", "alpha3", "numeric")
    FILTER_FIELDS = {"name": ("name", "official_name", "aliases")}
    SEARCH_FIELDS = {
        "name": 1.0,
        "official_name": 1.0,
        "aliases": 1.0,
    }

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["aliases"] = "|".join(self.aliases)
        data.pop("id")
        return tuple(data.values())

    @classmethod
    def from_row(cls, id: int, row: list[str | int | None], **kwargs) -> "CountryModel":
        ALIAS_IDX = 4
        NUMERIC_IDX = 5

        row[ALIAS_IDX] = [a for a in row[ALIAS_IDX].split("|") if a]
        row[NUMERIC_IDX] = int(row[NUMERIC_IDX])

        return cls(id, *row)
