from pathlib import Path
from ingest.utils import (
    COUNTRIES_INPUTS_PATH,
    COUNTRIES_MANIFEST_PATH,
    GEONAMES_DUMP_URL,
)
from ingest.utils import fetch
from ingest.shared.scripts.fetch_shared import CLDR_TERRITORY_INFO_URL, CLDR_TERRITORY_INFO_PATH

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
CLDR_CURRENCY_DATA_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-core/supplemental/currencyData.json"
CLDR_CURRENCY_DATA_PATH = COUNTRIES_INPUTS_PATH / "cldr_currency_data.json"


def _strip_comment_lines(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(
        "".join(l for l in lines if not l.startswith("#")), encoding="utf-8"
    )


def fetch_countries_sources(force: bool = False) -> bool:
    """Downloads whichever of ISO 3166-1, ISO 3166-3, GeoNames' country info, CLDR's currency data and CLDR's territory info changed; True if the stage should rebuild."""
    fetched = [
        fetch(ISO_COUNTRIES_URL, ISO_COUNTRIES_PATH, COUNTRIES_MANIFEST_PATH),
        fetch(ISO_HISTORIC_COUNTRIES_URL, ISO_HISTORIC_COUNTRIES_PATH, COUNTRIES_MANIFEST_PATH),
        fetch(GEONAMES_COUNTRIES_URL, GEONAMES_COUNTRIES_DEST, COUNTRIES_MANIFEST_PATH),
        fetch(CLDR_CURRENCY_DATA_URL, CLDR_CURRENCY_DATA_PATH, COUNTRIES_MANIFEST_PATH),
        # the shared stage's file, tracked in this manifest too, since subdivisions commits the shared manifest only after countries has dumped
        fetch(CLDR_TERRITORY_INFO_URL, CLDR_TERRITORY_INFO_PATH, COUNTRIES_MANIFEST_PATH),
    ]
    if fetched[2]:
        # GeoNames ships this with a '#' doc header the parser doesn't expect
        _strip_comment_lines(GEONAMES_COUNTRIES_DEST)
    return any(fetched) or force
