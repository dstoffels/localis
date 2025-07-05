from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class Country:
    name: str
    alpha2: str
    alpha3: str
    numeric: str
    long_name: str


@dataclass(frozen=True)
class Subdivision:
    """Represents a country subdivision such as a state, province, or territory."""

    name: str
    alt_name: str
    iso_code: str
    code: str
    category: str
    # subdivisions: list["Subdivision"]
    country: str
    country_alpha2: str
    country_alpha3: str


@dataclass(frozen=True)
class Locality:
    """Represents a geographic locality such as a city, town, village, or hamlet."""

    name: str
    subdivisions: list[Subdivision]
    country: str
    country_alpha2: str
    country_alpha3: str
    display_name: str
    lat: float
    lng: float
    classification: str | None
    osm_type: str
    osm_id: int
    population: int | None
