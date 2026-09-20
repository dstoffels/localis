from data.utils import (
    COUNTRIES_RAW_PATH,
    GEONAMES_DUMP_URL,
    download,
    strip_comment_lines,
)

ISO_CODES_COUNTRIES_URL = (
    "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json"
)


def fetch_countries_sources() -> None:
    # Fetch ISO 3166-1 country codes
    download(ISO_CODES_COUNTRIES_URL, COUNTRIES_RAW_PATH / "iso3166-1.json")

    # Fetch GeoNames country info
    geonames_dest = COUNTRIES_RAW_PATH / "geonames_countries.txt"
    download(f"{GEONAMES_DUMP_URL}/countryInfo.txt", geonames_dest)

    # GeoNames ships this with a '#' doc header the parser doesn't expect
    strip_comment_lines(geonames_dest)
