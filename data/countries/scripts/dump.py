from data.utils import *
from localis.models import CountryModel
from collections import defaultdict

COUNTRIES_DATA_PATH = DATA_PATH / "countries"


def dump(countries: list[CountryModel]) -> None:
    dump_data(countries, COUNTRIES_DATA_PATH / "countries.json.gz")
    dump_lookup_index(countries, COUNTRIES_DATA_PATH / "country_lookup_index.json.gz")
    dump_filter_index(countries, COUNTRIES_DATA_PATH / "country_filter_index.json.gz")
    dump_search_index(countries, COUNTRIES_DATA_PATH / "country_search_index.json.gz")
