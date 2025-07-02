import csv
from pathlib import Path
from .types import Country, Subdivision
from collections import defaultdict
from dataclasses import replace

DATA_DIR = Path(__file__).parent / "data"


def load_countries() -> list[Country]:
    countries = []
    with open(DATA_DIR / "countries.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            countries.append(
                Country(
                    alpha2=row["#country_code_alpha2"],
                    alpha3=row["country_code_alpha3"],
                    numeric=int(row["numeric_code"]),
                    name=row["name_short"],
                    name_long=row["name_long"],
                )
            )
    return countries


def load_subdivisions(countries_by_alpha2: dict[str, Country]) -> list[Subdivision]:
    subs = []
    with open(DATA_DIR / "subdivisions.csv", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alpha2 = row.get("subdivision_code_iso3166-2", "")
            country_code = row.get("#country_code_alpha2", "")
            country = countries_by_alpha2.get(country_code)
            subs.append(
                Subdivision(
                    iso_code=row.get("subdivision_code_iso3166-2", ""),
                    alpha2=alpha2.split("-")[-1] if "-" in alpha2 else alpha2,
                    name=row["subdivision_name"],
                    type=row["category"],
                    local_variant=row.get("localVariant", ""),
                    language_code=row.get("language_code", ""),
                    country_code=country_code,
                    country_name=country.name if country else "",
                )
            )
    return subs


def attach_subdivisions(
    countries: list[Country], subdivisions: list[Subdivision]
) -> list[Country]:
    subs_by_country = defaultdict(list)
    for sub in subdivisions:
        subs_by_country[sub.country_code].append(sub)
    return [replace(c, subdivisions=subs_by_country[c.alpha2]) for c in countries]
