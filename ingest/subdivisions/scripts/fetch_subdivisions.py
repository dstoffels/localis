from ingest.utils import has_changed, download
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

    # Check first: merging needs all sources locally, so if any one of them
    # changed, a partial fetch would leave the others missing.
    should_download = any(
        [
            has_changed(ADMIN1_URL, GEONAMES_ADMIN1_PATH, SUBDIVISIONS_MANIFEST_PATH),
            has_changed(ADMIN2_URL, GEONAMES_ADMIN2_PATH, SUBDIVISIONS_MANIFEST_PATH),
            has_changed(
                ISO_CODES_SUBDIVISIONS_URL,
                ISO_CODES_SUBS_PATH,
                SUBDIVISIONS_MANIFEST_PATH,
            ),
        ]
    )

    shared_downloaded = fetch_shared_sources(force=force)

    if not should_download and not shared_downloaded and not force:
        return False

    if should_download:
        download(ADMIN1_URL, GEONAMES_ADMIN1_PATH, SUBDIVISIONS_MANIFEST_PATH)
        download(ADMIN2_URL, GEONAMES_ADMIN2_PATH, SUBDIVISIONS_MANIFEST_PATH)
        download(
            ISO_CODES_SUBDIVISIONS_URL, ISO_CODES_SUBS_PATH, SUBDIVISIONS_MANIFEST_PATH
        )

    return True
