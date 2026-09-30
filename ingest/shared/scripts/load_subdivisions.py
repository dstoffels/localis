from ingest.utils import DATA_PATH, ingest_log
from ingest.shared.models import CountryModel, SubdivisionModel
import csv


def load_subdivisions(
    countries: dict[str, CountryModel],
) -> dict[str, SubdivisionModel]:
    ingest_log.writeline("Loading Subdivisions...")
    GEONAMES_CODE_INDEX = 1
    COUNTRY_INDEX = 7
    countries_by_id: dict[int, CountryModel] = {c.id: c for c in countries.values()}
    with open(
        DATA_PATH / "subdivisions" / "subdivisions.tsv", "r", encoding="utf-8"
    ) as f:

        subdivisions: dict[str, SubdivisionModel] = {}
        reader = csv.reader(f, delimiter="\t")
        for id, row in enumerate(reader, start=1):
            country = countries_by_id.get(int(row[COUNTRY_INDEX]))
            row = row[:COUNTRY_INDEX] + ([country] if country else [])
            subdivisions[row[GEONAMES_CODE_INDEX]] = SubdivisionModel(id, *row)
        return subdivisions
