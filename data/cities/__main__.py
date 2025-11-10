# This script parses geonames' allCountries.txt into a filtered TSV of cities with enriched data for country, subdivision and alternate city names as search tokens.
# Country and subdivision data are loaded from separate TSV files.
# Cities are filtered based on feature codes and population. We only want to include actual populated settlements as allCountries.txt contains many other geographical features.
# allCountries.txt (1.64GB) must be manually downloaded to the src folder from https://download.geonames.org/export/dump/

from pathlib import Path
from dataclasses import dataclass
import json
import csv
import re
from ..subdivisions.scripts.utils import SubdivisionDTO, SubdivisionMap

BASE_PATH = Path(__file__).parent


# helper DTO class
@dataclass
class CityDTO:
    name: str
    alt_names: list[str]
    lat: float
    lng: float
    country_alpha2: str
    admin1_code: str
    admin2_code: str
    admin3_code: str
    admin4_code: str
    population: int


# ***** LOADERS FOR COUNTRIES AND SUBDIVISIONS DATA *****

# countries: dict[str, str | None | list[str]] = {}


# def load_countries() -> dict[str, ]:
#     with open(BASE_PATH.parent / "countries/countries.tsv", "r", encoding="utf-8") as f:
#         reader = csv.DictReader(f, delimiter="\t")

#         for line in reader:
#             countries[line["alpha2"]] = line


def load_subdivisions() -> SubdivisionMap:
    sub_map = SubdivisionMap()
    with open(
        BASE_PATH.parent / "subdivisions/subdivisions.tsv", "r", encoding="utf-8"
    ) as f:
        reader = csv.DictReader(f, delimiter="\t")

        for row in reader:
            row["country_name"], row["country_alpha2"], row["country_alpha3"] = row.pop(
                "country"
            ).split("|")

            row["parent_id"] = row.pop("parent_rowid")

            row["admin_level"] = 2 if row["parent_id"] else 1
            sub_map.add(SubdivisionDTO(**row))

    return sub_map


subdivisions: SubdivisionMap = load_subdivisions()
print(len(subdivisions))


# ***** PARSER FOR GEONAMES LINES *****


def parse_geoname_line(line: str) -> tuple[CityDTO, str]:
    fields = line.strip().split("\t")
    if len(fields) != 19:
        raise ValueError(f"Expected 19 fields, got {len(fields)}")

    name = fields[1]
    alt_names = fields[3].split(",") if fields[3] else []
    ascii_name = fields[2]

    if name in alt_names:
        alt_names.remove(name)

    if ascii_name != name and ascii_name not in alt_names:
        alt_names.append(ascii_name)

    alt_names = "|".join(alt_names)

    lat = float(fields[4])
    lng = float(fields[5])

    country_alpha2 = fields[8]
    admin1_code = fields[10]
    admin2_code = fields[11]
    admin3_code = fields[12]
    admin4_code = fields[13]

    try:
        population = int(fields[14]) if fields[14] else 0
    except ValueError:
        raise ValueError(f"Invalid population value: {fields[14]}")

    feature_code = fields[7]

    return (
        CityDTO(
            name,
            alt_names,
            lat,
            lng,
            country_alpha2,
            admin1_code,
            admin2_code,
            admin3_code,
            admin4_code,
            population,
        ),
        feature_code,
    )


# ***** ROW BUILDING *****

rows: list[list[str]] = []


def get_sub(code: str) -> str:
    if not code:
        return ""
    sub = subdivisions.get(code)
    if not sub:
        return ""
    return f"{sub['name']}|{sub['code']}"


# def get_country(code: str) -> str:
#     c = countries[code]
#     return (
#         f"{c['name']}|{c['alpha2']}{f'|{c.get('alpha3')}' if c.get('alpha3') else ''}"
#     )


def parse_tokens(alt_names: str, name: str) -> str:
    STOPWORDS = {"the", "of", "and"}

    tokens: set[str] = set()

    names = alt_names.split("|")

    for n in names:
        parts = n.lower().strip().split()
        for p in parts:
            if p not in name.lower().split() and p not in STOPWORDS and len(p) > 2:
                tokens.add(p)

    return " ".join(sorted(tokens))


def build_row(city: CityDTO) -> list[str]:
    admin1_code = f"{city.country_alpha2}.{city.admin1_code}"
    admin2_code = f"{admin1_code}.{city.admin2_code}" if city.admin2_code else ""
    admin3_code = f"{admin2_code}.{city.admin3_code}" if city.admin3_code else ""
    admin4_code = f"{admin3_code}.{city.admin4_code}" if city.admin4_code else ""
    return [
        city.name,
        city.lat,
        city.lng,
        city.population,
        get_sub(admin1_code),
        get_sub(admin2_code),
        get_sub(admin3_code),
        get_sub(admin4_code),
        get_country(city.country_alpha2),
        parse_tokens(city.alt_names, city.name),
    ]


# ***** MAIN EXTRACTION AND TSV DUMPING *****


def extract_rows() -> None:
    load_countries()
    load_subdivisions()

    feature_codes = [
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
    ]

    with open(BASE_PATH / "allCountries.txt", "r", encoding="utf-8") as f:
        for line in f:
            city, feature_code = parse_geoname_line(line)
            if feature_code in feature_codes and int(city.population) > 0:
                rows.append(build_row(city))


def dump_to_tsv() -> None:
    HEADERS = (
        "name",
        "lat",
        "lng",
        "population",
        "admin1",
        "admin2",
        "admin3",
        "admin4",
        "country",
        "tokens",
    )

    with open(BASE_PATH / "cities.tsv", "w", encoding="utf-8", newline="") as f:

        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADERS)
        for row in rows:
            writer.writerow(row)


def main() -> None:
    extract_rows()
    dump_to_tsv()


if __name__ == "__main__":
    main()
