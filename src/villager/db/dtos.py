# These DTOS are the final product delivered to the user.

from dataclasses import dataclass, asdict
import json
from abc import ABC


@dataclass
class DTO(ABC):
    name: str

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict())


@dataclass
class Country(DTO):
    name: str
    official_name: str
    alpha2: str
    alpha3: str
    numeric: int
    alt_names: list[str]
    flag: str


@dataclass
class SubdivisionBasic:
    name: str
    geonames_code: str
    iso_code: str
    admin_level: int


@dataclass
class Subdivision(DTO):
    name: str
    alt_names: list[str]
    type: str
    geonames_code: str
    iso_code: str
    admin_level: int
    country: str
    country_alpha2: str
    country_alpha3: str
    parent_id: int | None


@dataclass
class City(DTO):
    name: str
    display_name: str | None
    subdivisions: list[SubdivisionBasic]
    country: str
    country_alpha2: str
    country_alpha3: str
    alt_names: list[str]
    population: int | None
    lat: float
    lng: float
