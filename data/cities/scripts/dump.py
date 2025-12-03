from data.utils import *
from localis.models import CityModel


def dump(cities: list[CityModel]) -> None:
    print(f"Dumping {len(cities)} cities...")
    dump_data(cities, DATA_PATH / "cities" / "cities.pkl.gz")

    print("Dumping cities lookup indexes...")
    dump_lookup_index(cities, DATA_PATH / "cities" / "cities_lookup_index.pkl.gz")

    print("Dumping cities filter index...")
    dump_filter_index(cities, DATA_PATH / "cities" / "cities_filter_index.pkl.gz")

    print("Dumping cities search index...")
    dump_search_index(cities, DATA_PATH / "cities" / "cities_search_index.pkl.gz")
