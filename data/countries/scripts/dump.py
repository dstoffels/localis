from data.utils import *
from localis.models import CountryModel

COUNTRIES_DATA_PATH = DATA_PATH / "countries"


def dump(countries: list[CountryModel]) -> None:
    dump_data(countries, COUNTRIES_DATA_PATH / "countries.pkl.gz")
    dump_lookup_index(countries, COUNTRIES_DATA_PATH / "country_lookup_index.pkl.gz")
    dump_filter_index(countries, COUNTRIES_DATA_PATH / "country_filter_index.pkl.gz")
    dump_search_index(countries, COUNTRIES_DATA_PATH / "country_search_index.pkl.gz")
