from ingest.utils import CITIES
from localis.utils.strings import is_latin
from ingest.utils import ingest_log
from ingest.shared.models import SubdivisionModel, CountryModel, CityModel
import csv

HEADERS = [
    "geonameid",
    "name",
    "asciiname",
    "alternatenames",
    "latitude",
    "longitude",
    "feature class",
    "feature code",
    "country code",
    "cc2",
    "admin1 code",
    "admin2 code",
    "admin3 code",
    "admin4 code",
    "population",
    "elevation",
    "dem",
    "timezone",
    "modification date",
]


def is_valid_city(row: dict[str, str]) -> bool:
    return bool(row["country code"])


def resolve_subdivision_chain(
    admin1: SubdivisionModel | None, admin2: SubdivisionModel | None
) -> list[SubdivisionModel]:
    """Walks the parent chain from the deepest resolved subdivision up to its root, ascending-admin_level ordered."""
    chain: list[SubdivisionModel] = []
    sub = admin2 or admin1
    while sub is not None:
        chain.append(sub)
        sub = sub.parent
    chain.reverse()
    return chain


def parse_row(
    row: dict[str, str],
    subdivisions: dict[str, SubdivisionModel],
    countries: dict[str, CountryModel],
) -> CityModel | None:

    geonames_id = row["geonameid"]

    # a name written in another script falls back to GeoNames' ASCII form
    name = row["name"] if is_latin(row["name"]) else row["asciiname"] or row["name"]

    admin1_raw = row["admin1 code"]
    admin2_raw = row["admin2 code"]
    country_code = row["country code"]

    admin1_code = ".".join([country_code, admin1_raw])
    admin2_code = ".".join([country_code, admin1_raw, admin2_raw])

    admin1 = subdivisions.get(admin1_code, None)
    admin2 = subdivisions.get(admin2_code, None)
    country = countries.get(country_code, None)

    if not country:
        ingest_log.writeline(
            f"country not found: {country_code}, dropping city {name} ({geonames_id})",
            level="WARN",
        )
        return None

    return CityModel(
        id=0,  # to be set before dump
        geonames_id=int(geonames_id),
        name=name,
        subdivisions=resolve_subdivision_chain(admin1, admin2),
        country=country,
        population=int(row["population"] or 0),
        lat=float(row["latitude"]),
        lng=float(row["longitude"]),
    )


def load_cities(
    subdivisions: dict[str, SubdivisionModel], countries: dict[str, CountryModel]
) -> tuple[list[CityModel], int]:
    """The parsed cities, and how many of them took GeoNames' ASCII name over a primary name in another script."""
    with open(CITIES.inputs / "cities500.txt", "r", encoding="utf-8") as f:
        ingest_log.writeline("Parsing cities from cities500.txt...")
        rows = csv.DictReader(f, fieldnames=HEADERS, delimiter="\t")
        cities = []
        ascii_names = 0
        for row in rows:
            if not is_valid_city(row):
                continue

            city = parse_row(row, subdivisions, countries)

            if not city:
                continue

            city.id = len(cities) + 1
            cities.append(city)
            if city.name != row["name"]:
                ascii_names += 1
        return cities, ascii_names
