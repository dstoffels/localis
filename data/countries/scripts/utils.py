from dataclasses import dataclass, field


# helper dto class
@dataclass
class CountryDTO:
    alpha2: str
    alpha3: str
    numeric: int
    name: str
    official_name: str
    aliases: list[str] = field(default_factory=list)
    names: list[str] = field(default_factory=list)
    geonames_id: str = ""
    qid: str = ""
    fips: str = ""
    flag: str = ""
