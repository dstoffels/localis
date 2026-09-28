from data.logger import log
from data.countries.ingest_countries import ingest_countries
from data.subdivisions.ingest_subdivisions import ingest_subdivisions
from data.cities.ingest_cities import ingest_cities


def ingest_all(interactive_mode: bool = False) -> None:
    log.clear()

    countries = ingest_countries()
    geocode_sub_map = ingest_subdivisions(countries, interactive_mode=interactive_mode)
    ingest_cities(countries, geocode_sub_map)


if __name__ == "__main__":
    ingest_all()
