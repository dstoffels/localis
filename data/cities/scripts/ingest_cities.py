import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

# This script parses geonames' cities500.txt into a TSV of cities with enriched data for country, subdivision and alternate city names as search tokens.
# Country and subdivision data are loaded from separate TSV files.
# cities500.txt is GeoNames' own pre-filtered export (population >= 500, or a seat of an
# administrative division regardless of population), so no further feature-code or
# population filtering is applied here, GeoNames already made that call.
# Fetched automatically by fetch_cities_sources() from https://download.geonames.org/export/dump/cities500.zip

from data.cities.scripts.fetch_cities import fetch_cities_sources
from data.cities.scripts.load_cities import load_cities
from data.cities.scripts.dump_cities import dump
from data.utils.index import load_countries, load_subdivisions
from data.utils.logger import log
from localis.models import SubdivisionModel, CountryModel, CityModel


def ingest_cities(
    countries: dict[str, CountryModel] = None,
    subdivisions: dict[str, SubdivisionModel] = None,
    force: bool = False,
) -> None:
    log.set_stage("CITIES")

    has_update = fetch_cities_sources(force=force)
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
