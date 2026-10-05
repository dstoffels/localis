from ingest.utils import SUBDIVISIONS, GEONAMES_DUMP_URL, fetch, iso_codes_url

ADMIN1_URL = f"{GEONAMES_DUMP_URL}/admin1CodesASCII.txt"
GEONAMES_ADMIN1_PATH = SUBDIVISIONS.inputs / "admin1CodesASCII.txt"

ADMIN2_URL = f"{GEONAMES_DUMP_URL}/admin2Codes.txt"
GEONAMES_ADMIN2_PATH = SUBDIVISIONS.inputs / "admin2Codes.txt"

ISO_CODES_SUBS_PATH = SUBDIVISIONS.inputs / "iso_3166-2.json"


def fetch_subdivisions_sources() -> None:
    """Downloads whichever of GeoNames' admin1/admin2 codes and ISO 3166-2 changed."""
    fetch(ADMIN1_URL, GEONAMES_ADMIN1_PATH, SUBDIVISIONS.manifest)
    fetch(ADMIN2_URL, GEONAMES_ADMIN2_PATH, SUBDIVISIONS.manifest)
    fetch(iso_codes_url(ISO_CODES_SUBS_PATH.name), ISO_CODES_SUBS_PATH, SUBDIVISIONS.manifest)
