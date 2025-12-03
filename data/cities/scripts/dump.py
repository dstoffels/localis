from data.utils import *
from localis.models import CityModel


def dump(cities: list[CityModel]) -> None:
    print(f"Dumping {len(cities)} cities...")
    dump_data(cities, DATA_PATH / "cities" / "cities.pkl.gz")

    print("Dumping city indexes...")
    dump_lookup_index(cities, DATA_PATH / "cities" / "city_lookup_index.pkl.gz")

    print("Dumping city filter index...")
    dump_filter_index(cities, DATA_PATH / "cities" / "city_filter_index.pkl.gz")

    print("Dumping city search index...")
    dump_search_index(cities, DATA_PATH / "cities" / "city_search_index.pkl.gz")
