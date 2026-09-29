from data.utils.paths import DATA_PATH
from data.utils.index import (
    dump_data,
    dump_lookup_index,
    dump_filter_index,
    dump_search_index,
)
from localis.models import CityModel
from data.utils.logger import log

CITIES_DATA_PATH = DATA_PATH / "cities"


def dump(cities: list[CityModel]) -> None:
    log.writeline(f"Dumping {len(cities)} cities...")
    dump_data(cities, CITIES_DATA_PATH / "cities.tsv")

    log.writeline("Dumping cities lookup indexes...")
    dump_lookup_index(cities, CITIES_DATA_PATH)

    log.writeline("Dumping cities filter index...")
    dump_filter_index(cities, CITIES_DATA_PATH)

    log.writeline("Dumping cities search index...")
    dump_search_index(cities, CITIES_DATA_PATH)
