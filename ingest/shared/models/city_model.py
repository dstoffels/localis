from dataclasses import dataclass
from .model import Model
from .country_model import CountryModel
from .subdivision_model import SubdivisionModel


@dataclass(slots=True)
class CityModel(Model):
    geonames_id: int
    admin1: SubdivisionModel | None
    admin2: SubdivisionModel | None
    country: CountryModel | None
    population: int
    lat: float
    lng: float

    LOOKUP_FIELDS = ("geonames_id",)
    FILTER_FIELDS = {
        "name": ("name",),
        "country": (
            "country.name",
            "country.alpha2",
            "country.alpha3",
        ),
        "subdivision": (
            "admin1.name",
            "admin1.iso_suffix",
            "admin1.iso_code",
            "admin1.geonames_code",
            "admin2.name",
            "admin2.iso_code",
            "admin2.geonames_code",
        ),
    }
    SEARCH_FIELDS = {
        "name": 1.0,
        "admin1.name": 0.6,
        "admin1.iso_suffix": 0.6,
        "country.name": 0.3,
        "country.alpha2": 0.3,
        "country.alpha3": 0.3,
    }

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["admin1"] = self.admin1.id if self.admin1 else None
        data["admin2"] = self.admin2.id if self.admin2 else None
        data["country"] = self.country.id if self.country else None
        data.pop("id")
        return tuple(data.values())
