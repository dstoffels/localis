from dataclasses import dataclass, asdict, field
import json
from abc import ABC, abstractmethod


class DTOBase(ABC):
    @classmethod
    @abstractmethod
    def from_row(cls, row: tuple):
        pass

    def to_dict(self):
        return asdict(self)

    def json(self):
        return json.dumps(self.to_dict())

    def __str__(self):
        return self.json(indent=2)


c = (
    232,
    "United States Minor Outlying Islands",
    "united states minor outlying islands",
    "UM",
    "UMI",
    581,
    "United States Minor Outlying Islands (the)",
)


@dataclass
class Country(DTOBase):
    name: str
    alpha2: str
    alpha3: str
    numeric: str
    long_name: str

    @classmethod
    def from_row(cls, tuple: tuple) -> "Country":
        return Country(
            name=tuple[1],
            alpha2=tuple[3],
            alpha3=tuple[4],
            numeric=tuple[5],
            long_name=tuple[6],
        )


@dataclass
class SubdivisionBase(DTOBase):
    name: str
    iso_code: str
    code: str
    category: str
    admin_level: int

    @classmethod
    def from_row(cls, tuple: tuple) -> "SubdivisionBase":
        return SubdivisionBase(
            name=tuple[0],
            iso_code=tuple[1],
            code=tuple[2],
            category=tuple[3],
            admin_level=tuple[4],
        )


@dataclass
class Subdivision(SubdivisionBase):
    """Represents a country subdivision such as a state, province, or territory."""

    alt_name: str
    country: str
    country_alpha2: str
    country_alpha3: str

    @classmethod
    def from_row(cls, tuple: tuple) -> "Subdivision":
        return Subdivision(
            name=tuple[1],
            iso_code=tuple[3],
            alt_name=tuple[4],
            code=tuple[5],
            category=tuple[6],
            admin_level=tuple[9],
            country=tuple[12],
            country_alpha2=tuple[14],
            country_alpha3=tuple[15],
        )


@dataclass
class Locality(DTOBase):
    """Represents a geographic locality such as a city, town, village, or hamlet."""

    osm_id: int
    osm_type: str
    name: str
    display_name: str
    classification: str | None
    population: int | None
    lat: float
    lng: float
    country: str
    country_alpha2: str
    country_alpha3: str
    subdivisions: list[SubdivisionBase] = field(default_factory=list)

    @classmethod
    def from_row(cls, tuple: tuple) -> "Locality":
        return Locality(
            osm_id=tuple[0],
            osm_type=tuple[1],
            name=tuple[2],
            display_name=tuple[3],
            classification=tuple[4],
            population=tuple[5],
            lat=tuple[6],
            lng=tuple[7],
            country=tuple[8],
            country_alpha2=tuple[9],
            country_alpha3=tuple[10],
            subdivisions=[],
        )
