import argparse

from data.utils.logger import log
from data.countries.scripts.ingest_countries import ingest_countries
from data.subdivisions.scripts.ingest_subdivisions import ingest_subdivisions
from data.cities.scripts.ingest_cities import ingest_cities


def ingest_all(force: bool = False) -> None:
    log.clear()

    countries = ingest_countries(force)
    geocode_submap = ingest_subdivisions(countries, force=force)
    ingest_cities(countries, geocode_submap, force=force)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-ingestion of all data sources regardless of whether they have changed",
    )

    args = parser.parse_args()
    ingest_all(force=args.force)


if __name__ == "__main__":
    main()
