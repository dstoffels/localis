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
        dto.admin1 = self.admin1 and extract_base(self.admin1)
        dto.admin2 = self.admin2 and extract_base(self.admin2)
        dto.country = self.country and extract_base(self.country)
        return dto

    def to_row(self) -> tuple[str | int | None]:
        data = self.to_dict()
        data["admin1"] = self.admin1.id if self.admin1 else None
        data["admin2"] = self.admin2.id if self.admin2 else None
        data["country"] = self.country.id if self.country else None
        return tuple(data.values())

    @classmethod
    def from_row(
        cls,
        row: tuple[str | int | None],
        countries: dict[int, list],
        subdivisions: dict[int, list],
        **kwargs,
    ) -> DTO | None:
        """Builds a CityModel instance from a raw data tuple (row) and injects country and subdivision models from their respective caches. Returns the final DTO for the user."""
        if not row:
            return None

        flat_model: "CityModel" = cls(*row)

        country_data = countries.get(flat_model.country)
        if country_data:
            flat_model.country = CountryModel.from_row(country_data)

        admin1_data = subdivisions.get(flat_model.admin1)
        if admin1_data:
            flat_model.admin1 = SubdivisionModel.from_row(
                admin1_data, countries=countries, subdivisions=subdivisions
            )

        admin2_data = subdivisions.get(flat_model.admin2)
        if admin2_data:
            flat_model.admin2 = SubdivisionModel.from_row(
                admin2_data, countries=countries, subdivisions=subdivisions
            )

        return flat_model.dto

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
