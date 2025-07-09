from dataclasses import dataclass, asdict, field
import json


class DTOBase:
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
    def from_row(self, tuple: tuple):
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


@dataclass
class Subdivision(SubdivisionBase):
    """Represents a country subdivision such as a state, province, or territory."""

    alt_name: str
    country: str
    country_alpha2: str
    country_alpha3: str


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
