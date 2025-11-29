from dataclasses import dataclass
from .model import DTO, Model, extract_base
from .country import CountryBase, CountryModel
from .subdivision import SubdivisionBase, SubdivisionModel
from sys import intern


@dataclass(slots=True)
class City(DTO):
    # display_name: str
    ascii_name: str
    admin1: SubdivisionBase
    admin2: SubdivisionBase
    country: CountryBase
    population: int
    lat: float
    lng: float


@dataclass(slots=True)
class CityModel(City, Model):
    admin1: SubdivisionModel
    admin2: SubdivisionModel
    country: CountryModel

    @property
    def dto(self) -> City:
        dto: City = extract_base(self, depth=1)
        dto.admin1 = self.admin1 and extract_base(self.admin1, depth=2)
        dto.admin2 = self.admin2 and extract_base(self.admin2, depth=2)
        dto.country = self.country and extract_base(self.country, depth=2)
        return dto

    def set_search_meta(self):
        base = [
            self.name.lower().replace(" ", ""),
            self.ascii_name.lower().replace(" ", ""),
        ]

        admin1 = (self.admin1.search_context or "") if self.admin1 else ""

        country = (self.country.search_context or "") if self.country else ""

        self.search_fields = [
            base[0],
            base[1],
            admin1,
            country,
        ]

        # Fuzzy context stays full
        self.search_context = " ".join(
            [
                self.ascii_name,
                self.admin1.search_context if self.admin1 else "",
                self.country.search_context if self.country else "",
            ]
        ).lower()
