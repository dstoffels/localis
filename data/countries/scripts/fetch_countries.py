from data.utils import COUNTRIES_RAW_PATH, GEONAMES_DUMP_URL, download
from data.paths import COUNTRIES_MANIFEST_PATH, Path

ISO_CODES_COUNTRIES_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json"
)


def _strip_comment_lines(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    path.write_text(
        "".join(l for l in lines if not l.startswith("#")), encoding="utf-8"
    )


def fetch_countries_sources() -> bool:
    # Fetch ISO 3166-1 country data
    iso_codes_dest = COUNTRIES_RAW_PATH / "iso_3166-1.json"
    iso_changed = download(ISO_CODES_COUNTRIES_URL, iso_codes_dest, COUNTRIES_MANIFEST_PATH)

    # Fetch GeoNames country data
    geonames_dest = COUNTRIES_RAW_PATH / "geonames_countries.txt"
    geonames_changed = download(
        f"{GEONAMES_DUMP_URL}/countryInfo.txt", geonames_dest, COUNTRIES_MANIFEST_PATH
    )
    if geonames_changed:
        # GeoNames ships this with a '#' doc header the parser doesn't expect
        _strip_comment_lines(geonames_dest)

    return iso_changed or geonames_changed
