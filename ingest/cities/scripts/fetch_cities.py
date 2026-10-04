from ingest.utils import fetch
from ingest.utils import CITIES_INPUTS_PATH, CITIES_MANIFEST_PATH, GEONAMES_DUMP_URL


def fetch_cities_sources(force: bool = False) -> bool:
    """Downloads GeoNames' cities500 if it changed; True if the stage should rebuild."""
    fetched = fetch(f"{GEONAMES_DUMP_URL}/cities500.zip", CITIES_INPUTS_PATH / "cities500.zip", CITIES_MANIFEST_PATH, extract="cities500.txt")
    return fetched or force
