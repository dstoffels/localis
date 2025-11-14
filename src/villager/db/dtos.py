# These DTOS are the final product delivered to the user.

from dataclasses import dataclass, asdict
import json
from abc import ABC


@dataclass
class DTO(ABC):
    id: int
    name: str

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self):
        return self.json()


@dataclass
class Country(DTO):
    id: int
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
    id: int
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
    id: int
    geonames_id: int
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
