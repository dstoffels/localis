import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

# This script parses geonames' allCountries.txt into a filtered TSV of cities with enriched data for country, subdivision and alternate city names as search tokens.
# Country and subdivision data are loaded from separate TSV files.
# Cities are filtered based on feature codes and population. We only want to include actual populated settlements as allCountries.txt contains many other geographical features.
# allCountries.txt (1.64GB) must be manually downloaded to the src folder from https://download.geonames.org/export/dump/

from data.cities.scripts.fetch_cities import fetch_cities_sources
from data.cities.scripts.load_cities import load_cities
from data.cities.scripts.dump_cities import dump
from data.utils.index import load_countries, load_subdivisions
from data.logger import log
from localis.models import SubdivisionModel, CountryModel, CityModel


def ingest_cities(
    countries: dict[str, CountryModel] = None,
    subdivisions: dict[str, SubdivisionModel] = None,
) -> None:
    log.set_stage("CITIES")

    has_update = fetch_cities_sources()
    if not has_update:
        log.writeline("No updates for cities.")
        return None

    if countries is None:
        countries = load_countries()
    if subdivisions is None:
        subdivisions = load_subdivisions(countries)

    cities: list[CityModel] = load_cities(subdivisions, countries)
    dump(cities)
    log.writeline(f"completed: {len(cities)} cities")


if __name__ == "__main__":
    ingest_cities()
