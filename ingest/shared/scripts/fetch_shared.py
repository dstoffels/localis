from ingest.utils import fetch
from ingest.utils import SHARED_INPUTS_PATH, SHARED_MANIFEST_PATH, GEONAMES_DUMP_URL

ALT_NAMES_URL = f"{GEONAMES_DUMP_URL}/alternateNamesV2.zip"
ALT_NAMES_ZIP_PATH = SHARED_INPUTS_PATH / "alternateNamesV2.zip"
ALT_NAMES_PATH = SHARED_INPUTS_PATH / "alternateNamesV2.txt"

CLDR_TERRITORY_INFO_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-core/supplemental/territoryInfo.json"
CLDR_TERRITORY_INFO_PATH = SHARED_INPUTS_PATH / "cldr_territory_info.json"


def fetch_shared_sources(force: bool = False) -> bool:
    """Downloads whichever of GeoNames' alternate names and CLDR's territory info changed; True if the stages using them should rebuild."""
    fetched = [
        fetch(ALT_NAMES_URL, ALT_NAMES_ZIP_PATH, SHARED_MANIFEST_PATH, extract=ALT_NAMES_PATH.name),
        fetch(CLDR_TERRITORY_INFO_URL, CLDR_TERRITORY_INFO_PATH, SHARED_MANIFEST_PATH),
    ]
    return any(fetched) or force
