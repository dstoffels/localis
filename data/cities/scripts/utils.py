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
    admin1: str
    admin2: str
    country: str
    population: int
    lat: float
    lng: float


def load_countries() -> dict[str, str]:
    """loads a dict of concatenated country data by its alpha2"""
    print("Loading Countries...")
    countries: dict[str, str] = {}
    with open(BASE_PATH.parent / "countries/countries.tsv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            countries[row["alpha2"]] = "|".join(
                [row["name"], row["alpha2"], row["alpha3"]]
            )
    return countries


def load_subdivisions() -> dict[str, str]:
    """loads a dict of concatenated subdivision data by its geonames code"""
    print("Loading Subdivisions...")
    subdivisions: dict[str, str] = {}
    with open(
        BASE_PATH.parent / "subdivisions/subdivisions.tsv", "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            subdivisions[row["geonames_code"]] = "|".join(
                [row["name"], row["geonames_code"], row["iso_code"]]
            )

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
