from .utils import *


def dump_to_tsv(cities: list[CityDTO]) -> None:
    HEADERS = (
        "geonames_id",
        "name",
        "alt_names",
        "admin1",
        "admin2",
        "country",
        "population",
        "lat",
        "lng",
    )

    with open(BASE_PATH / "cities.tsv", "w", encoding="utf-8", newline="") as f:
        print(f"Writing {len(cities)} cities to cities.tsv...")
        writer = csv.writer(f, delimiter="\t")
        writer.writerow(HEADERS)
        for city in cities:
            writer.writerow(city.__dict__.values())
