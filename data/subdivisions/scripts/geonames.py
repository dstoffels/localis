from pathlib import Path
from .utils import *


def load_geonames_file(
    file_name: Path, countries: dict[str, CountryDTO], sub_map: SubdivisionMap
) -> None:
    with open(BASE_PATH / file_name, "r", encoding="utf-8") as f:
        for line in f:
            # code, name, name_ascii, geonames_id
            parts = line.strip().split("\t")
            name = parts[1]
            ascii_name = parts[2] if parts[2] != name else None
            geonames_code = parts[0]

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

            subdivision = SubdivisionDTO(
                name=name,
                country_id=country.id,
                country_alpha2=country.alpha2,
                country_alpha3=country.alpha3,
                country_name=country.name,
                geonames_code=geonames_code,
                parent_code=parent_code,
                admin_level=admin_level,
            )

            if ascii_name and ascii_name not in subdivision.alt_names:
                subdivision.alt_names.append(ascii_name)

            subdivision.alt_names = dedupe(subdivision.alt_names)

            sub_map.add(subdivision)


def map_subdivisions(
    countries: dict[str, CountryDTO],
) -> SubdivisionMap:
    print("Loading GeoNames subdivisions...")
    sub_map = SubdivisionMap()
    load_geonames_file("src/admin1CodesASCII.txt", countries, sub_map)
    load_geonames_file("src/admin2.txt", countries, sub_map)
    return sub_map
