from pathlib import Path
from dataclasses import dataclass
import csv
import unicodedata
from unidecode import unidecode

BASE_PATH = Path(__file__).parent.parent


# helper DTO class
@dataclass
class CityDTO:
    geonames_id: int
    name: str
    alt_names: list[str]
    admin1_id: int
    # admin1_str: str
    admin2_id: int
    # admin2_str: str
    country_id: int
    # country_str: str
    population: int
    lat: float
    lng: float


def load_countries() -> dict[str, int]:
    """loads a dict of country codes mapped to their ids"""
    print("Loading Countries...")
    countries: dict[str, int] = {}
    with open(BASE_PATH.parent / "countries/countries.tsv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for id, row in enumerate(reader, 1):
            countries[row["alpha2"]] = id
    return countries


def load_subdivisions() -> dict[str, int]:
    """loads a dict of subdivision geonames codes mapped to their ids"""
    print("Loading Subdivisions...")
    subdivisions: dict[str, int] = {}
    with open(
        BASE_PATH.parent / "subdivisions/subdivisions.tsv", "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f, delimiter="\t")

        for id, row in enumerate(reader, 1):
            subdivisions[row["geonames_code"]] = id

    return subdivisions


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    return "".join(char for char in name.lower() if not unicodedata.combining(char))


ALLOWED_CHARS = set(" -'’")


def is_latin(name: str) -> bool:
    for c in name:
        if c.isalpha():
            try:
                if "LATIN" not in unicodedata.name(c):
                    return False
            except ValueError:
                return False
        elif c not in ALLOWED_CHARS:
            return False
    return True
