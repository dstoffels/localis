from data.utils.paths import CITIES_RAW_PATH
from data.cities.utils.strings import normalize_name, is_latin
from data.logger import log
from localis.models import SubdivisionModel, CountryModel, CityModel
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


ALLOWED_FEATURE_CODES = {
    "PPL",
    "PPLA",
    "PPLA2",
    "PPLA3",
    "PPLA4",
    "PPLA5",
    "PPLC",
    "PPLF",
    "PPLL",
    "PPLS",
    "STLMT",
}


def is_valid_city(
    row: dict[str, str], allowed_codes: set[str] = ALLOWED_FEATURE_CODES
) -> bool:
    return (
        row["feature code"]
        in allowed_codes  # filter out anything that's not a populated place
        and row["population"]
        not in ["", "0"]  # filter out places with no population data
        and row["country code"]  # filter out places with no country code
    )


def filter_names(row: dict[str, str]) -> tuple[str]:
    """Keep Latin-based alt names, filter junk and dedupe"""
    name = row["name"]
    alt_names = row["alternatenames"].split(",") if row["alternatenames"] else []
    alt_names.append(row["asciiname"])

    seen = set()
    base = normalize_name(name)
    result = []

    for alt in alt_names:
        # filter out shorties, lots of noise
        alt = alt.strip()
        if len(alt) < 3:
            continue

        # filter out non-latin based names, dataset would be massive
        if not is_latin(alt):
            continue

        norm = normalize_name(alt)
        if norm == base or norm in seen:
            continue

        seen.add(norm)
        result.append(alt.title())

    return name, "|".join(result)


def parse_row(
    row: dict[str, str],
    subdivisions: dict[str, SubdivisionModel],
    countries: dict[str, CountryModel],
) -> CityModel:

    geonames_id = row["geonameid"]

    name = row["name"]

    admin1_raw = row["admin1 code"]
    admin2_raw = row["admin2 code"]
    country_code = row["country code"]

    admin1_code = ".".join([country_code, admin1_raw])
    admin2_code = ".".join([country_code, admin1_raw, admin2_raw])

    admin1 = subdivisions.get(admin1_code, None)
    admin2 = subdivisions.get(admin2_code, None)
    country = countries.get(country_code, None)

    if not country:
        log.writeline(
            f"country not found: {country_code}, dropping city {name} ({geonames_id})"
        )
        return None

    lat = row["latitude"]
    lng = row["longitude"]

    try:
        population = row["population"] if row["population"] else 0
    except ValueError:
        raise ValueError(f"Invalid population value: {row['population']}")

    return CityModel(
        id=0,  # to be set before dump
        geonames_id=int(geonames_id),
        name=name,
        admin1=admin1,
        admin2=admin2,
        country=country,
        population=int(population),
        lat=float(lat),
        lng=float(lng),
    )


def load_cities(
    subdivisions: dict[str, SubdivisionModel], countries: dict[str, CountryModel]
) -> list[CityModel]:
    with open(CITIES_RAW_PATH / "allCountries.txt", "r", encoding="utf-8") as f:
        print(f"Parsing cities from allCountries.txt...")
        rows = csv.DictReader(f, fieldnames=HEADERS, delimiter="\t")
        cities = []
        for row in rows:
            if not is_valid_city(row):
                continue

            city = parse_row(row, subdivisions, countries)

            if not city:
                continue

            city.id = len(cities) + 1
            cities.append(city)
        return cities
