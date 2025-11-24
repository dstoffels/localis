from .utils import *


def dump_to_tsv(cities: list[CityDTO]) -> None:
    HEADERS = (
        # "id",
        # "geonames_id",
        "name",
        # "alt_names",
        "admin1_id",
        "admin2_id",
        "country_id",
        "population",
        "lat",
        "lng",
    )

    with open(BASE_PATH / "cities.tsv", "w", encoding="utf-8", newline="") as f:
        print(f"Writing {len(cities)} cities to cities.tsv...")

        writer = csv.DictWriter(f, delimiter="\t", fieldnames=HEADERS)
        writer.writeheader()
        for city in cities:
            writer.writerow(
                {
                    # "id": id,
                    "name": city.name,
                    "admin1_id": city.admin1_id,
                    "admin2_id": city.admin2_id,
                    "country_id": city.country_id,
                    "population": city.population,
                    "lat": city.lat,
                    "lng": city.lng,
                }
            )
