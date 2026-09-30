from ingest.utils import DATA_PATH
from ingest.utils import (
    dump_data,
    dump_lookup_index,
    dump_filter_index,
    dump_search_index,
)
from ingest.shared.models import CountryModel
from ingest.utils import ingest_log

COUNTRIES_DATA_PATH = DATA_PATH / "countries"


def dump(countries: list[CountryModel]) -> None:
    ingest_log.writeline(f"Dumping {len(countries)} countries...")
    dump_data(countries, COUNTRIES_DATA_PATH / "countries.tsv")

    ingest_log.writeline("Dumping countries lookup indexes...")
    dump_lookup_index(countries, COUNTRIES_DATA_PATH)

    ingest_log.writeline("Dumping countries filter index...")
    dump_filter_index(countries, COUNTRIES_DATA_PATH)

    ingest_log.writeline("Dumping countries search index...")
    dump_search_index(countries, COUNTRIES_DATA_PATH)
