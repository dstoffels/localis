from dataclasses import dataclass, field
from ...countries.__main__ import CountryDTO
import csv
import unicodedata
from unidecode import unidecode
import hashlib
from pathlib import Path

BASE_PATH = Path(__file__).parent.parent


# helper dto class
@dataclass
class SubdivisionDTO:
    name: str
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

    # deterministically hash a unique id to later map admin2 subdivisions to their parent
    def __post_init__(self):
        # if self.id != -1:
        key_parts = [
            self.country_alpha2,
            str(self.admin_level),
            normalize(self.name).lower(),
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


class SubdivisionMap:
    def __init__(self):
        self._subs: dict[str, dict[int, dict[int, SubdivisionDTO]]] = {}
        self._by_id: dict[int, SubdivisionDTO] = {}
        self._by_geo_code: dict[str, SubdivisionDTO] = {}
        self._by_iso_code: dict[str, SubdivisionDTO] = {}

    def add(self, sub: SubdivisionDTO) -> None:
        country_map = self._subs.setdefault(sub.country_alpha2, {})
        level_map = country_map.setdefault(sub.admin_level, {})
        level_map[sub.id] = sub
        self._by_id[sub.id] = sub
        if sub.iso_code:
            self._by_iso_code[sub.iso_code] = sub
        if sub.geonames_code:
            self._by_geo_code[sub.geonames_code] = sub

    def get(
        self, id: int = None, geo_code: str = None, iso_code: str = None
    ) -> SubdivisionDTO:
        if id is not None:
            return self._by_id.get(id)
        if geo_code is not None:
            return self._by_geo_code.get(geo_code)
        if iso_code is not None:
            return self._by_iso_code.get(iso_code)

    def filter(
        self, country_alpha2: str, admin_level: int = None
    ) -> list[SubdivisionDTO]:
        if admin_level is not None:
            return list(
                self._subs.get(country_alpha2, {}).get(admin_level, {}).values()
            )
        else:
            return [
                sub
                for level_map in self._subs.get(country_alpha2, {}).values()
                for sub in level_map.values()
            ]

    def all(self) -> SubdivisionDTO:
        return [
            sub
            for country_map in self._subs.values()
            for level_map in country_map.values()
            for sub in level_map.values()
        ]

    def refresh(self):
        self._subs, self._by_geo_code, self._by_iso_code = {}, {}, {}
        for sub in self._by_id.values():
            self.add(sub)
            if sub.parent_code and not sub.parent_id:
                if "-" in sub.parent_code:
                    sub.parent_id = self._by_iso_code[sub.parent_code].id
                elif "." in sub.parent_code:
                    sub.parent_id = self._by_geo_code[sub.parent_code].id

    def get_final(self) -> list[SubdivisionDTO]:
        """Returns an ordered list of all subdivisions to align the rowid to all parent ids for db normalization"""
        all_subs: list[SubdivisionDTO] = sorted(
            self.all(), key=lambda s: (s.country_alpha2, s.admin_level, s.name)
        )

        id_map = {sub.id: i for i, sub in enumerate(all_subs, start=1)}

        for sub in all_subs:
            sub.id = id_map[sub.id]
            sub.parent_id = id_map.get(sub.parent_id)

        return all_subs

    def __len__(self):
        return len(self._by_id)


def load_countries() -> dict[str, CountryDTO]:
    print("Loading countries...")
    with open(BASE_PATH.parent / "countries/countries.tsv", "r", encoding="utf-8") as f:
        csv_reader = csv.DictReader(f, delimiter="\t")
        return {
            row["alpha2"]: CountryDTO(
                name=row["name"],
                official_name=row["official_name"],
                alpha2=row["alpha2"],
                alpha3=row["alpha3"],
                numeric=row["numeric"],
                alt_names=row["alt_names"].split("|") if row["alt_names"] else [],
            )
            for row in csv_reader
        }


def dedupe(items: list[str]) -> list[str]:
    seen = {}
    for s in items:
        key = s.lower()
        if key not in seen or len(s) < len(seen[key]):
            seen[key] = s
    return sorted(seen.values())


def normalize(s: str) -> str:
    MAP = {"ə": "a", "ǝ": "ä"}

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = "".join(MAP.get(ch, ch) for ch in s)
    s = unidecode(s)
    return s.strip()


def is_iso_code(code: str) -> bool:
    return "-" in code
