from ingest.utils import DATA_PATH
from ingest.utils import (
    dump_data,
    dump_lookup_index,
    dump_filter_index,
    dump_search_index,
)
from ingest.shared.models import CityModel
from ingest.utils import ingest_log

CITIES_DATA_PATH = DATA_PATH / "cities"


def dump(cities: list[CityModel]) -> None:
    ingest_log.writeline(f"Dumping {len(cities)} cities...")
    dump_data(cities, CITIES_DATA_PATH / "cities.tsv")

    ingest_log.writeline("Dumping cities lookup indexes...")
    dump_lookup_index(cities, CITIES_DATA_PATH)

    ingest_log.writeline("Dumping cities filter index...")
    dump_filter_index(cities, CITIES_DATA_PATH)

    ingest_log.writeline("Dumping cities search index...")
    dump_search_index(cities, CITIES_DATA_PATH)
