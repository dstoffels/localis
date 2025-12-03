from dataclasses import dataclass
from .model import DTO, Model, extract_base
from .country import CountryBase, CountryModel
from .subdivision import SubdivisionBase, SubdivisionModel


@dataclass(slots=True)
class City(DTO):
    geonames_id: str
    admin1: SubdivisionBase
    admin2: SubdivisionBase
    country: CountryBase
    population: int
    lat: float
    lng: float


@dataclass(slots=True)
class CityModel(City, Model):
    LOOKUP_FIELDS = ("geonames_id",)
    FILTER_FIELDS = {
        "name": ("name",),
        "country": (
            "country.alpha2",
            "country.alpha3",
        ),
        "subdvision": (
            "admin1.iso_code",
            "admin1.geonames_code",
            "admin2.iso_code",
            "admin2.geonames_code",
        ),
    }
    SEARCH_FIELDS = {
        "name": 1.0,
        "admin1.iso_suffix": 0.5,
        "admin1.name": 0.5,
        "country.alpha2": 0.4,
        "country.alpha3": 0.4,
        "country.name": 0.4,
    }

    admin1: SubdivisionModel | None
    admin2: SubdivisionModel | None
    country: CountryModel | None

    @property
    def dto(self) -> City:
        dto: City = extract_base(self, depth=1)
        dto.admin1 = self.admin1 and extract_base(self.admin1, depth=2)
        dto.admin2 = self.admin2 and extract_base(self.admin2, depth=2)
        dto.country = self.country and extract_base(self.country, depth=2)
        return dto

    def to_row(self) -> list:
        data = self.to_dict()
        data["admin1"] = self.admin1.id if self.admin1 else None
        data["admin2"] = self.admin2.id if self.admin2 else None
        data["country"] = self.country.id if self.country else None
        return [*data.values()]

    # _search_context: str | None = None

    # @property
    # def search_context(self) -> str:
    #     if self._search_context is None:
    #         self._search_context = " ".join(
    #             [
    #                 self.name,
    #                 self.admin1.iso_suffix if self.admin1 else "",
    #                 self.admin1.name if self.admin1 else "",
    #                 self.country.name if self.country else "",
    #                 self.country.alpha2 if self.country else "",
    #                 self.country.alpha3 if self.country else "",
    #             ]
    #         ).lower()
    #     return self._search_context
