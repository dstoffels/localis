from .utils import *

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
) -> CityDTO:

    geonames_id = row["geonameid"]

    name, alt_names = filter_names(row)

    admin1_raw = row["admin1 code"]
    admin2_raw = row["admin2 code"]
    country_code = row["country code"]

    admin1 = ".".join([country_code, admin1_raw])
    admin2 = ".".join([country_code, admin1_raw, admin2_raw])

    admin1_id = subdivisions.get(admin1, None)
    admin2_id = subdivisions.get(admin2, None)
    country_id = countries.get(country_code, None)

    lat = float(row["latitude"])
    lng = float(row["longitude"])

    try:
        population = int(row["population"]) if row["population"] else 0
    except ValueError:
        raise ValueError(f"Invalid population value: {row['population']}")

    return CityDTO(
        geonames_id=geonames_id,
        name=name,
        alt_names=alt_names,
        admin1_id=admin1_id,
        admin2_id=admin2_id,
        country_id=country_id,
        # admin1_str=admin1,
        # admin2_str=admin2,
        # country_str=country,
        population=population,
        lat=lat,
        lng=lng,
    )


def load_cities(
    subdivisions: dict[str, int], countries: dict[str, int]
) -> list[CityDTO]:
    with open(BASE_PATH / "src/allCountries.txt", "r", encoding="utf-8") as f:
        print(f"Parsing cities from allCountries.txt...")
        rows = csv.DictReader(f, fieldnames=HEADERS, delimiter="\t")
        cities = []
        for row in rows:
            if not is_valid_city(row):
                continue
            city = parse_row(row, subdivisions, countries)
            cities.append(city)
        return cities
