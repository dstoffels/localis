from data.utils import COUNTRIES_RAW_PATH, GEONAMES_DUMP_URL, has_changed, download
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
    iso_codes_dest = COUNTRIES_RAW_PATH / "iso_3166-1.json"
    geonames_url = f"{GEONAMES_DUMP_URL}/countryInfo.txt"
    geonames_dest = COUNTRIES_RAW_PATH / "geonames_countries.txt"

    # Check first: if either source changed, we need both files locally to merge,
    # so a partial fetch (only the changed one) would leave the other missing.
    any_changed = any(
        [
            has_changed(
                ISO_CODES_COUNTRIES_URL, iso_codes_dest, COUNTRIES_MANIFEST_PATH
            ),
            has_changed(geonames_url, geonames_dest, COUNTRIES_MANIFEST_PATH),
        ]
    )

    if not any_changed:
        return False

    download(ISO_CODES_COUNTRIES_URL, iso_codes_dest, COUNTRIES_MANIFEST_PATH)

    download(geonames_url, geonames_dest, COUNTRIES_MANIFEST_PATH)
    # GeoNames ships this with a '#' doc header the parser doesn't expect
    _strip_comment_lines(geonames_dest)

    return True
