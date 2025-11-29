from data.utils import CityData, CITIES_SRC_PATH, generate_trigrams, normalize
from data.cities.scripts.utils import *

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
    return row["feature code"] in allowed_codes and row["population"] not in ["", "0"]


def filter_names(row: dict[str, str]) -> tuple[str]:
    """Keep Latin-based alt names, filter junk and dedupe"""
    name = row["name"]
    alt_names = row["alternatenames"].split(",") if row["alternatenames"] else []
    alt_names.append(row["asciiname"])

    seen = set()
    base = normalize_name(name)
    result = []

    for alt in alt_names:
        alt = alt.strip()
        if len(alt) < 3:  # filter out shorties
            continue
        if not is_latin(alt):  # filter out non-latin based names
            continue

        norm = normalize_name(alt)
        if norm == base or norm in seen:
            continue

        seen.add(norm)
        result.append(alt.title())

    return name, "|".join(result)


def parse_row(
    row: dict[str, str], subdivisions: dict[str, int], countries: dict[str, int]
) -> CityData:

    geonames_id = row["geonameid"]

    name = row["name"]
    ascii_name = row["asciiname"] if row["asciiname"].lower() != name.lower() else ""

    admin1_raw = row["admin1 code"]
    admin2_raw = row["admin2 code"]
    country_code = row["country code"]

    admin1 = ".".join([country_code, admin1_raw])
    admin2 = ".".join([country_code, admin1_raw, admin2_raw])

    admin1_id = subdivisions.get(admin1, None)
    admin2_id = subdivisions.get(admin2, None)
    country_id = countries.get(country_code, None)

    lat = row["latitude"]
    lng = row["longitude"]

    try:
        population = row["population"] if row["population"] else 0
    except ValueError:
        raise ValueError(f"Invalid population value: {row['population']}")

    return CityData(
        geonames_id=geonames_id,
        name=name,
        ascii_name=ascii_name,
        alt_names=[],
        admin1_id=admin1_id,
        admin2_id=admin2_id,
        country_id=country_id,
        population=population,
        lat=lat,
        lng=lng,
        search_tokens="|".join(set(generate_trigrams(normalize(name)))),
    )


def load_cities(
    subdivisions: dict[str, int], countries: dict[str, int]
) -> list[CityData]:
    with open(CITIES_SRC_PATH / "allCountries.txt", "r", encoding="utf-8") as f:
        print(f"Parsing cities from allCountries.txt...")
        rows = csv.DictReader(f, fieldnames=HEADERS, delimiter="\t")
        cities = []
        for row in rows:
            if is_valid_city(row):
                city = parse_row(row, subdivisions, countries)
                cities.append(city)
        return cities
