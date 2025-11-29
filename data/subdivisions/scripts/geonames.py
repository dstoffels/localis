from pathlib import Path
from data.subdivisions.utils import *
from data.utils import SUB_SRC_PATH, normalize
import csv


def load_geonames_file(
    file_name: Path, countries: dict[str, CountryData], sub_map: SubdivisionMap
) -> None:
    with open(SUB_SRC_PATH / file_name, "r", encoding="utf-8") as f:
        HEADERS = ["code", "name", "name_ascii", "geonames_id"]
        reader = csv.DictReader(
            f,
            fieldnames=HEADERS,
            delimiter="\t",
        )
        for row in reader:
            # code, name, name_ascii, geonames_id
            name: str = row["name"]
            geonames_code: str = row["code"]

            # determine parent code and set admin level
            code_parts = geonames_code.split(".")
            if len(code_parts) == 2:
                country_alpha2, _ = code_parts
                parent_code = None
                admin_level = 1
            elif len(code_parts) == 3:
                country_alpha2, parent_code, _ = code_parts
                parent_code = f"{country_alpha2}.{parent_code}"
                admin_level = 2

            country = countries.get(country_alpha2)
            if not country:
                print(f"Country {country_alpha2} not found, skipping {name}.")
                continue

            subdivision = SubdivisionData(
                name=name,
                country_id=country.id,
                country_alpha2=country.alpha2,
                country_alpha3=country.alpha3,
                country_name=country.name,
                geonames_code=geonames_code,
                parent_code=parent_code,
                admin_level=admin_level,
            )

            sub_map.add(subdivision)


def map_subdivisions(
    countries: dict[str, CountryData],
) -> SubdivisionMap:
    print("Loading GeoNames subdivisions...")
    sub_map = SubdivisionMap()
    load_geonames_file("admin1CodesASCII.txt", countries, sub_map)
    load_geonames_file("admin2.txt", countries, sub_map)
    return sub_map
