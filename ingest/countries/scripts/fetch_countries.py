from pathlib import Path
from ingest.utils import (
    COUNTRIES_INPUTS_PATH,
    COUNTRIES_MANIFEST_PATH,
    GEONAMES_DUMP_URL,
)
from ingest.utils import has_changed, download

ISO_COUNTRIES_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json"
)
ISO_COUNTRIES_PATH = COUNTRIES_INPUTS_PATH / "iso_3166-1.json"
ISO_HISTORIC_COUNTRIES_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-3.json"
)
ISO_HISTORIC_COUNTRIES_PATH = COUNTRIES_INPUTS_PATH / "iso_3166-3.json"
GEONAMES_COUNTRIES_URL = f"{GEONAMES_DUMP_URL}/countryInfo.txt"
GEONAMES_COUNTRIES_DEST = COUNTRIES_INPUTS_PATH / "geonamesInfo.txt"


def _strip_comment_lines(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(
        "".join(l for l in lines if not l.startswith("#")), encoding="utf-8"
    )


def fetch_countries_sources(force: bool = False) -> bool:

    # Check first: if either source changed, we need both files locally to merge,
    # so a partial fetch would leave the other missing.
    should_download = any(
        [
            has_changed(ISO_COUNTRIES_URL, ISO_COUNTRIES_PATH, COUNTRIES_MANIFEST_PATH),
            has_changed(
                ISO_HISTORIC_COUNTRIES_URL,
                ISO_HISTORIC_COUNTRIES_PATH,
                COUNTRIES_MANIFEST_PATH,
            ),
            has_changed(
                GEONAMES_COUNTRIES_URL, GEONAMES_COUNTRIES_DEST, COUNTRIES_MANIFEST_PATH
            ),
        ]
    )

    if not should_download and not force:
        return False

    if should_download:
        download(ISO_COUNTRIES_URL, ISO_COUNTRIES_PATH, COUNTRIES_MANIFEST_PATH)

        download(
            ISO_HISTORIC_COUNTRIES_URL,
            ISO_HISTORIC_COUNTRIES_PATH,
            COUNTRIES_MANIFEST_PATH,
        )

        download(
            GEONAMES_COUNTRIES_URL, GEONAMES_COUNTRIES_DEST, COUNTRIES_MANIFEST_PATH
        )
        # GeoNames ships this with a '#' doc header the parser doesn't expect
        _strip_comment_lines(GEONAMES_COUNTRIES_DEST)

    return True
