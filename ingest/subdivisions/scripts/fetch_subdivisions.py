from ingest.utils import has_changed, download
from ingest.utils import (
    SUBDIVISIONS_RAW_PATH,
    SUBDIVISIONS_MANIFEST_PATH,
    GEONAMES_DUMP_URL,
)

ISO_CODES_SUBDIVISIONS_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-2.json"
)

IPREGISTRY_SUBDIVISIONS_URL = (
    "https://raw.githubusercontent.com/ipregistry/iso3166/main/subdivisions.csv"
)


def fetch_subdivisions_sources(force: bool = False) -> bool:
    admin1_url = f"{GEONAMES_DUMP_URL}/admin1CodesASCII.txt"
    geonames_admin1_dest = SUBDIVISIONS_RAW_PATH / "admin1CodesASCII.txt"

    admin2_url = f"{GEONAMES_DUMP_URL}/admin2Codes.txt"
    geonames_admin2_dest = SUBDIVISIONS_RAW_PATH / "admin2Codes.txt"

    iso_codes_dest = SUBDIVISIONS_RAW_PATH / "iso_3166-2.json"
    ipregistry_dest = SUBDIVISIONS_RAW_PATH / "ipregistry_subdivisions.csv"

    # Check first: merging needs all four sources locally, so if any one of them
    # changed, a partial fetch would leave the others missing.
    should_download = any(
        [
            has_changed(admin1_url, geonames_admin1_dest, SUBDIVISIONS_MANIFEST_PATH),
            has_changed(admin2_url, geonames_admin2_dest, SUBDIVISIONS_MANIFEST_PATH),
            has_changed(
                ISO_CODES_SUBDIVISIONS_URL, iso_codes_dest, SUBDIVISIONS_MANIFEST_PATH
            ),
            has_changed(
                IPREGISTRY_SUBDIVISIONS_URL, ipregistry_dest, SUBDIVISIONS_MANIFEST_PATH
            ),
        ]
    )

    if not should_download and not force:
        return False

    if should_download:
        download(admin1_url, geonames_admin1_dest, SUBDIVISIONS_MANIFEST_PATH)
        download(admin2_url, geonames_admin2_dest, SUBDIVISIONS_MANIFEST_PATH)
        download(
            ISO_CODES_SUBDIVISIONS_URL, iso_codes_dest, SUBDIVISIONS_MANIFEST_PATH
        )
        download(
            IPREGISTRY_SUBDIVISIONS_URL, ipregistry_dest, SUBDIVISIONS_MANIFEST_PATH
        )

    return True
