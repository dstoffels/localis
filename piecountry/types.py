from dataclasses import dataclass, field
from typing import List


@dataclass(frozen=True)
class Country:
    name: str
    alpha2: str
    alpha3: str
    numeric: str
    name_long: str
    subdivisions: List["Subdivision"] = field(default_factory=list, compare=False)


@dataclass(frozen=True)
class Subdivision:
    name: str
    iso_code: str
    alpha2: str
    type: str
    local_variant: str
    country_code: str
    country_name: str
    language_code: str
