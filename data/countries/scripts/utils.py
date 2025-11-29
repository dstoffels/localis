from dataclasses import dataclass, field
from pathlib import Path


BASE_PATH = Path(__file__).parent.parent


# helper dto class
@dataclass
class CountryDTO:
    id: str
    name: str
    ascii_name: str
    official_name: str
    alt_names: list[str]
    alpha2: str
    alpha3: str
    numeric: int
    flag: str

    def dump(self):
        # final dedupe before dump
        self.alt_names = "|".join(set(self.alt_names) - {self.name, self.official_name})
        return [*self.__dict__.values()]
