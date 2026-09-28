from data.utils import download
from data.paths import (
    SUBDIVISIONS_RAW_PATH,
    SUBDIVISIONS_MANIFEST_PATH,
    GEONAMES_DUMP_URL,
)

IPREGISTRY_SUBDIVISIONS_URL = (
    "https://raw.githubusercontent.com/ipregistry/iso3166/main/subdivisions.csv"
)


def fetch_subdivisions_sources() -> bool:
    # fetch geonames data
    admin1_url = f"{GEONAMES_DUMP_URL}/admin1CodesASCII.txt"
    geonames_admin1_dest = SUBDIVISIONS_RAW_PATH / "admin1CodesASCII.txt"
    admin1_changed = download(
        admin1_url,
        geonames_admin1_dest,
        SUBDIVISIONS_MANIFEST_PATH,
    )

    admin2_url = f"{GEONAMES_DUMP_URL}/admin2Codes.txt"
    geonames_admin2_dest = SUBDIVISIONS_RAW_PATH / "admin2Codes.txt"

    admin2_changed = download(
        admin2_url,
        geonames_admin2_dest,
        SUBDIVISIONS_MANIFEST_PATH,
    )

    # fetch ipregistry data
    ipregistry_dest = SUBDIVISIONS_RAW_PATH / "iso-3166-2.csv"
    ipregistry_changed = download(
        IPREGISTRY_SUBDIVISIONS_URL, ipregistry_dest, SUBDIVISIONS_MANIFEST_PATH
    )

    return admin1_changed or admin2_changed or ipregistry_changed
