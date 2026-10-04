from ingest.utils import fetch
from ingest.utils import (
    SUBDIVISIONS_INPUTS_PATH,
    SUBDIVISIONS_MANIFEST_PATH,
    GEONAMES_DUMP_URL,
)
from ingest.shared.scripts import fetch_shared_sources

ISO_CODES_SUBDIVISIONS_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-2.json"
)

ADMIN1_URL = f"{GEONAMES_DUMP_URL}/admin1CodesASCII.txt"
GEONAMES_ADMIN1_PATH = SUBDIVISIONS_INPUTS_PATH / "admin1CodesASCII.txt"

ADMIN2_URL = f"{GEONAMES_DUMP_URL}/admin2Codes.txt"
GEONAMES_ADMIN2_PATH = SUBDIVISIONS_INPUTS_PATH / "admin2Codes.txt"

ISO_CODES_SUBS_PATH = SUBDIVISIONS_INPUTS_PATH / "iso_3166-2.json"


def fetch_subdivisions_sources(force: bool = False) -> bool:
    """Downloads whichever of GeoNames' admin1/admin2 codes, ISO 3166-2 and the shared sources changed; True if the stage should rebuild."""
    fetched = [
        fetch(ADMIN1_URL, GEONAMES_ADMIN1_PATH, SUBDIVISIONS_MANIFEST_PATH),
        fetch(ADMIN2_URL, GEONAMES_ADMIN2_PATH, SUBDIVISIONS_MANIFEST_PATH),
        fetch(ISO_CODES_SUBDIVISIONS_URL, ISO_CODES_SUBS_PATH, SUBDIVISIONS_MANIFEST_PATH),
        fetch_shared_sources(force=force),
    ]
    return any(fetched) or force
