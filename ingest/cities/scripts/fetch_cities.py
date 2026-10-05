from ingest.utils import CITIES, GEONAMES_DUMP_URL, fetch


def fetch_cities_sources() -> None:
    """Downloads GeoNames' cities500 if it changed."""
    fetch(f"{GEONAMES_DUMP_URL}/cities500.zip", CITIES.inputs / "cities500.zip", CITIES.manifest, extract="cities500.txt")
