import csv
from ingest.utils import DATA_PATH, ingest_log
from ingest.shared.models import CountryModel


def load_countries() -> dict[str, CountryModel]:
    ALPHA2_INDEX = 1
    ingest_log.writeline("Loading countries...")
    with open(DATA_PATH / "countries" / "countries.tsv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        return {
            row[ALPHA2_INDEX]: CountryModel(id, *row)
            for id, row in enumerate(reader, start=1)
        }
