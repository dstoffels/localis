from data.utils import *
from localis.models import CityModel


def dump(cities: list[CityModel]) -> None:
    print(f"Dumping {len(cities)} cities...")
    dump_data(cities, DATA_PATH / "cities" / "cities.json.gz")

    print("Dumping city indexes...")
    dump_lookup_index(cities, DATA_PATH / "cities" / "city_lookup_index.json.gz")

    print("Dumping city filter index...")
    dump_filter_index(cities, DATA_PATH / "cities" / "city_filter_index.json.gz")

    print("Dumping city search index...")
    dump_search_index(cities, DATA_PATH / "cities" / "city_search_index.json.gz")

    # # Dump to search index
    # with open(DATA_PATH / "city_search_index.json", "w", encoding="utf-8") as f:
    #     search_index = {}
    #     for id, city in enumerate(cities, 1):
    #         for token in city.extract_search_tokens():
    #             if token not in search_index:
    #                 search_index[token] = []
    #             search_index[token].append(id)
    #     json.dump(search_index, f, ensure_ascii=False, indent=2, separators=(",", ": "))

    # # Dump to city TSV file
    # HEADERS = (
    #     "name",
    #     "admin1_id",
    #     "admin2_id",
    #     "country_id",
    #     "population",
    #     "lat",
    #     "lng",
    #     "search_tokens",
    # )

    # with open(DATA_PATH / "cities.tsv", "w", encoding="utf-8", newline="") as f:
    #     print(f"Writing {len(cities)} cities to cities.tsv...")

    #     writer = csv.DictWriter(f, delimiter="\t", fieldnames=HEADERS)
    #     writer.writeheader()
    #     for city in cities:
    #         writer.writerow(
    #             {
    #                 "name": city.name,
    #                 "admin1_id": city.admin1_id,
    #                 "admin2_id": city.admin2_id,
    #                 "country_id": city.country_id,
    #                 "population": city.population,
    #                 "lat": city.lat,
    #                 "lng": city.lng,
    #                 "search_tokens": city.search_tokens,
    #             }
    #         )
