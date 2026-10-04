# Builds cities from GeoNames' cities500, linked to the countries and subdivisions built upstream; cities500 is already filtered (population >= 500 or an administrative seat), so no further filtering is applied.

from .fetch_cities import fetch_cities_sources
from .load_cities import load_cities
from ingest.shared.scripts import load_countries, load_subdivisions
from ingest.utils import ingest_log, commit_manifest, dump_registry, CITIES_MANIFEST_PATH
from ingest.shared.models import SubdivisionModel, CountryModel, CityModel


def ingest_cities(
    countries: dict[str, CountryModel] | None = None,
    subdivisions: dict[str, SubdivisionModel] | None = None,
    force: bool = False,
) -> None:
    ingest_log.set_stage("CITIES")

    try:
        has_update = fetch_cities_sources(force=force)
        # rows and indexes store country ids and the full subdivision chain, so countries or subdivisions rebuilt upstream (passed in) force a rebuild even when cities500 is unchanged
        if not has_update and countries is None and subdivisions is None:
            ingest_log.writeline("No updates for cities, subdivisions or countries.")
            return None

        if countries is None:
            countries = load_countries()
        if subdivisions is None:
            subdivisions = load_subdivisions(countries)

        cities: list[CityModel] = load_cities(subdivisions, countries)
        dump_registry("cities", cities)
        commit_manifest(CITIES_MANIFEST_PATH)
        ingest_log.writeline(f"completed: {len(cities)} cities")
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_cities()
