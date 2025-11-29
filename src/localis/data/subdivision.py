from dataclasses import dataclass
from .model import DTO, Model, extract_base
from .country import CountryBase, CountryModel
from sys import intern


@dataclass(slots=True)
class SubdivisionBase(DTO):
    geonames_code: str | None
    iso_code: str | None
    type: str


@dataclass(slots=True)
class Subdivision(SubdivisionBase):
    aliases: list[str]
    admin_level: int
    parent: SubdivisionBase | None
    country: CountryBase


@dataclass(slots=True)
class SubdivisionModel(Subdivision, Model):
    parent: "SubdivisionModel"
    country: CountryModel

    @property
    def dto(self):
        dto: Subdivision = extract_base(self)
        dto.parent = self.parent and extract_base(self.parent, depth=2)
        dto.country = self.country and extract_base(self.country, depth=2)
        return dto

    def set_search_meta(self):
        iso_code = self.iso_code.split("-")[1] if self.iso_code else ""

        self.search_fields = (
            self.name.lower(),
            iso_code.lower(),
            *(a.lower() for a in self.aliases),
        )

        country_context = self.country.search_context if self.country else ""

        self.search_context = f'{" ".join(self.search_fields)} {country_context}'
