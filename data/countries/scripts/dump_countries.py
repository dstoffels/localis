from data.utils.paths import DATA_PATH
from data.utils.index import (
    dump_data,
    dump_lookup_index,
    dump_filter_index,
    dump_search_index,
)
from localis.models import CountryModel

COUNTRIES_DATA_PATH = DATA_PATH / "countries"


def dump(countries: list[CountryModel]) -> None:
    dump_data(countries, COUNTRIES_DATA_PATH / "countries.tsv")
    dump_lookup_index(countries, COUNTRIES_DATA_PATH)
    dump_filter_index(countries, COUNTRIES_DATA_PATH)
    dump_search_index(countries, COUNTRIES_DATA_PATH)
