# This script parses geonames' cities500.txt into a TSV of cities with enriched data for country, subdivision and alternate city names as search tokens.
# Country and subdivision data are loaded from separate TSV files.
# cities500.txt is GeoNames' own pre-filtered export (population >= 500, or a seat of an
# administrative division regardless of population), so no further feature-code or
# population filtering is applied here, GeoNames already made that call.
# Fetched automatically by fetch_cities_sources() from https://download.geonames.org/export/dump/cities500.zip

from .fetch_cities import fetch_cities_sources
from .load_cities import load_cities
from .dump_cities import dump
from ingest.shared.scripts import load_countries, load_subdivisions
from ingest.utils import ingest_log
from ingest.shared.models import SubdivisionModel, CountryModel, CityModel


def ingest_cities(
    countries: dict[str, CountryModel] | None = None,
    subdivisions: dict[str, SubdivisionModel] | None = None,
    force: bool = False,
) -> None:
    ingest_log.set_stage("CITIES")

    try:
        has_update = fetch_cities_sources(force=force)
        if not has_update:
            ingest_log.writeline("No updates for cities.")
            return None

        if countries is None:
            countries = load_countries()
        if subdivisions is None:
            subdivisions = load_subdivisions(countries)

        cities: list[CityModel] = load_cities(subdivisions, countries)
        dump(cities)
        ingest_log.writeline(f"completed: {len(cities)} cities")
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_cities()
