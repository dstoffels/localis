from data.utils import *
from localis.models import CountryModel

COUNTRIES_DATA_PATH = DATA_PATH / "countries"


def dump(countries: list[CountryModel]) -> None:
    dump_data(countries, COUNTRIES_DATA_PATH / "countries.tsv")
    dump_lookup_index(countries, COUNTRIES_DATA_PATH / "countries_lookup_index.tsv")
    dump_filter_index(countries, COUNTRIES_DATA_PATH / "countries_filter_index.tsv")
    dump_search_index(countries, COUNTRIES_DATA_PATH / "countries_search_index.tsv")
