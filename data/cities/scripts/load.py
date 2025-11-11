from .utils import *

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
    fields: list[str], allowed_codes: set[str] = ALLOWED_FEATURE_CODES
) -> bool:
    return fields[7] in allowed_codes and fields[14] not in ["", "0"]


def filter_names(fields: list[str]) -> tuple[str]:
    """Keep Latin-based alt names, filter junk and dedupe"""
    name = fields[1]
    alt_names = fields[3].split(",") if fields[3] else []
    alt_names.append(fields[2])

    seen = set()
    base = normalize_name(name)
    result = []

    for alt in alt_names:
        alt = alt.strip()
        if len(alt) < 3:
            continue
        if not is_latin(alt):
            continue

        norm = normalize_name(alt)
        if norm == base or norm in seen:
            continue

        seen.add(norm)
        result.append(alt.title())

    return name, "|".join(result)


def parse_fields(
    fields: list[str], subdivisions: dict[str, str], countries: dict[str, str]
) -> CityDTO:
    if len(fields) != 19:
        raise ValueError(f"Expected 19 fields, got {len(fields)}")

    name, alt_names = filter_names(fields)

    admin1_code = fields[10]
    admin2_code = fields[11]
    country_code = fields[8]

    country = countries.get(country_code)
    admin1 = subdivisions.get(".".join([country_code, admin1_code]))
    admin2 = subdivisions.get(".".join([country_code, admin2_code]))

    lat = float(fields[4])
    lng = float(fields[5])

    try:
        population = int(fields[14]) if fields[14] else 0
    except ValueError:
        raise ValueError(f"Invalid population value: {fields[14]}")

    return CityDTO(
        name=name,
        alt_names=alt_names,
        admin1=admin1,
        admin2=admin2,
        country=country,
        population=population,
        lat=lat,
        lng=lng,
    )


def load_cities(
    subdivisions: dict[str, str], countries: dict[str, str]
) -> list[CityDTO]:
    with open(BASE_PATH / "src/allCountries.txt", "r", encoding="utf-8") as f:
        print(f"Parsing cities from allCountries.txt...")
        cities = []
        for row in f:
            fields = row.split("\t")
            if not is_valid_city(fields):
                continue
            city = parse_fields(fields, subdivisions, countries)
            cities.append(city)
        return cities
