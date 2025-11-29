from dataclasses import dataclass, field
import hashlib
from pathlib import Path
from localis.utils import normalize, generate_token_trigrams

BASE_PATH = Path(__file__).parent
FIXTURE_PATH = BASE_PATH.parent / "src" / "localis" / "data" / "fixtures"
COUNTRIES_SRC_PATH = BASE_PATH / "countries" / "src"
SUB_SRC_PATH = BASE_PATH / "subdivisions" / "src"
CITIES_SRC_PATH = BASE_PATH / "cities" / "src"


@dataclass
class CountryData:
    id: str
    name: str
    official_name: str
    alt_names: list[str]
    alpha2: str
    alpha3: str
    numeric: int
    flag: str
    search_tokens: str = ""

    def dump(self):
        # final dedupe before dump
        self.alt_names = "|".join(set(self.alt_names) - {self.name, self.official_name})

        self.search_tokens = " ".join(set(generate_token_trigrams(self.name)))

        data = self.__dict__
        data.pop("id")
        return [*data.values()]


@dataclass
class SubdivisionData:
    name: str
    country_id: int
    country_alpha2: str
    country_alpha3: str
    country_name: str
    admin_level: int
    geonames_code: str = ""
    iso_code: str = ""
    type: str = ""
    alt_names: list[str] = field(default_factory=list)
    id: int = field(init=False)
    parent_id: int | None = None
    parent_code: str | None = None  # Can be iso or GeoNames code, detect later
    search_tokens: str = ""

    # deterministically hash a unique id to later map admin2 subdivisions to their parents and to manually map ISO subdivisions that cannot be automatically merged with its geonames counterpart. id is ONLY used internally for these purposes; once the subdvision data has been successfully merged, the hashed id is discarded.
    def __post_init__(self):
        key_parts = [
            self.country_alpha2,
            str(self.admin_level),
            normalize(self.name),
            self.iso_code or self.geonames_code,  # whichever comes first at creation
        ]
        key = "|".join(key_parts)
        self.id = int.from_bytes(hashlib.md5(key.encode()).digest()[:8], "big")

    def concat_country(self) -> str:
        return "|".join(
            [self.country_name, self.country_alpha2, self.country_alpha3 or ""]
        )

    def concat(self) -> str:
        return "|".join([self.name, self.geonames_code, self.iso_code])
