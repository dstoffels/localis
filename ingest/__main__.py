import argparse

from ingest.macroregions.scripts import ingest_macroregions
from ingest.currencies.scripts import ingest_currencies
from ingest.scripts.scripts import ingest_scripts
from ingest.countries.scripts import ingest_countries
from ingest.subdivisions.scripts import ingest_subdivisions
from ingest.cities.scripts import ingest_cities


def ingest_all(force: bool = False) -> None:
    macroregions = ingest_macroregions(force)
    currencies = ingest_currencies(force)
    ingest_scripts(force)
    countries = ingest_countries(macroregions, currencies, force=force)
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
