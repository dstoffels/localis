from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.utils import SUBDIVISIONS
from ingest.utils import ingest_log
import csv
from ingest.shared.models import CountryModel
from ingest.shared.models import SubdivisionModel


def load_geonames_file(
    file_name: str, countries: dict[str, CountryModel], sub_map: SubdivisionMap
) -> None:
    with open(SUBDIVISIONS.inputs / file_name, "r", encoding="utf-8") as f:
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
            geonames_id: int = int(row["geonames_id"])

            # CC.A1 is an admin1 code, CC.A1.A2 an admin2 one; the parent is linked by SubdivisionMap.refresh()
            code_parts = geonames_code.split(".")
            if len(code_parts) not in (2, 3):
                raise ValueError(f"unexpected geonames code format: {geonames_code}")
            country_alpha2 = code_parts[0]
            admin_level = len(code_parts) - 1

            country = countries.get(country_alpha2)
            if not country:
                ingest_log.writeline(
                    f"country not found: {country_alpha2}, skipping {name}",
                    level="WARN",
                )
                continue

            subdivision = SubdivisionModel(
                id=0,  # temporary, will be set when all loaded
                name=name,
                country=country,
                geonames_code=geonames_code,
                geonames_id=geonames_id,
                parent=None,
                admin_level=admin_level,
                iso_code=None,  # may be set later if merged with ISO subdivision
                type=None,  # GeoNames does not provide type info in these files, may be set by ISO data
                aliases=[],  # may be set later if merged with ISO subdivision
            )
            subdivision.set_hashid()
            sub_map.add(subdivision)


def map_geonames_subdivisions(
    countries: dict[str, CountryModel],
) -> SubdivisionMap:
    ingest_log.writeline("Loading GeoNames subdivisions...")
    sub_map = SubdivisionMap()
    load_geonames_file("admin1CodesASCII.txt", countries, sub_map)
    load_geonames_file("admin2Codes.txt", countries, sub_map)
    return sub_map
