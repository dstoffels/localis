from pathlib import Path
from data.subdivisions.utils.subdivision_map import SubdivisionMap
from data.utils.paths import SUBDIVISIONS_RAW_PATH
from data.logger import log
import csv
from localis.models import CountryModel, SubdivisionModel


def load_geonames_file(
    file_name: Path, countries: dict[str, CountryModel], sub_map: SubdivisionMap
) -> None:
    with open(SUBDIVISIONS_RAW_PATH / file_name, "r", encoding="utf-8") as f:
        HEADERS = ("code", "name", "name_ascii", "geonames_id")
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
                # parent_code = None
                parent = None
                admin_level = 1
            elif len(code_parts) == 3:
                country_alpha2, parent_code, _ = code_parts
                parent_code = f"{country_alpha2}.{parent_code}"
                parent = sub_map.get(geo_code=parent_code)
                admin_level = 2

            country = countries.get(country_alpha2)
            if not country:
                log.writeline(f"country not found: {country_alpha2}, skipping {name}")
                continue

            subdivision = SubdivisionModel(
                id=0,  # temporary, will be set when all loaded
                name=name,
                country=country,
                geonames_code=geonames_code,
                parent=parent,
                admin_level=admin_level,
                iso_code=None,  # may be set later if merged with ISO subdivision
                type=None,  # GeoNames does not provide type info in these files, may be set by ISO data
                aliases=[],  # may be set later if merged with ISO subdivision
            )
            subdivision.id = subdivision.hashid  # set hashid for internal mapping
            sub_map.add(subdivision)


def map_geonames_subdivisions(
    countries: dict[str, CountryModel],
) -> SubdivisionMap:
    log.writeline("Loading GeoNames subdivisions...")
    sub_map = SubdivisionMap()
    load_geonames_file("admin1CodesASCII.txt", countries, sub_map)
    load_geonames_file("admin2Codes.txt", countries, sub_map)
    return sub_map
