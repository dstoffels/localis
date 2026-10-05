from ingest.utils import SHARED, GEONAMES_DUMP_URL, cldr_url, fetch

ALT_NAMES_URL = f"{GEONAMES_DUMP_URL}/alternateNamesV2.zip"
ALT_NAMES_ZIP_PATH = SHARED.inputs / "alternateNamesV2.zip"
ALT_NAMES_PATH = SHARED.inputs / "alternateNamesV2.txt"

CLDR_TERRITORY_INFO_PATH = SHARED.inputs / "cldr_territory_info.json"


def fetch_shared_sources() -> None:
    """Downloads whichever of GeoNames' alternate names and CLDR's territory info changed."""
    fetch(ALT_NAMES_URL, ALT_NAMES_ZIP_PATH, SHARED.manifest, extract=ALT_NAMES_PATH.name)
    fetch(cldr_url("cldr-core/supplemental/territoryInfo.json"), CLDR_TERRITORY_INFO_PATH, SHARED.manifest)
