# This stage builds cities from GeoNames' cities500, linked to the countries and subdivisions built before it; cities500 is already filtered (population >= 500 or an administrative seat), so no further filtering is applied.

import json
from .fetch_cities import fetch_cities_sources
from .load_cities import load_cities
from ingest.utils import CITIES, ingest_log, dump_registry, stage_text
from ingest.shared.models import CityModel, SubdivisionModel, CountryModel

# counts only the pipeline can see, read by tests/analysis/data_stats.py
INGEST_STATS_PATH = CITIES.outputs / "ingest_stats.json"


def ingest_cities(countries: dict[str, CountryModel], subdivisions: dict[str, SubdivisionModel]) -> list[CityModel]:
    with ingest_log.stage(CITIES):
        fetch_cities_sources()
        cities, ascii_names = load_cities(subdivisions, countries)
        dump_registry("cities", cities)
        stage_text(INGEST_STATS_PATH, json.dumps({"ascii_names": ascii_names}, indent=2) + "\n")
        ingest_log.writeline(f"completed: {len(cities)} cities")
        return cities
