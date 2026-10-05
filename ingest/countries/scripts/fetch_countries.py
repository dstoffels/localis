from ingest.utils import COUNTRIES, GEONAMES_DUMP_URL, fetch

ISO_COUNTRIES_URL = "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-1.json"
ISO_COUNTRIES_PATH = COUNTRIES.inputs / "iso_3166-1.json"
ISO_HISTORIC_COUNTRIES_URL = "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_3166-3.json"
ISO_HISTORIC_COUNTRIES_PATH = COUNTRIES.inputs / "iso_3166-3.json"
GEONAMES_COUNTRIES_URL = f"{GEONAMES_DUMP_URL}/countryInfo.txt"
GEONAMES_COUNTRIES_DEST = COUNTRIES.inputs / "geonamesInfo.txt"
CLDR_CURRENCY_DATA_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-core/supplemental/currencyData.json"
CLDR_CURRENCY_DATA_PATH = COUNTRIES.inputs / "cldr_currency_data.json"


def fetch_countries_sources() -> None:
    """Downloads whichever of ISO 3166-1, ISO 3166-3, GeoNames' country info and CLDR's currency data changed."""
    fetch(ISO_COUNTRIES_URL, ISO_COUNTRIES_PATH, COUNTRIES.manifest)
    fetch(ISO_HISTORIC_COUNTRIES_URL, ISO_HISTORIC_COUNTRIES_PATH, COUNTRIES.manifest)
    fetch(GEONAMES_COUNTRIES_URL, GEONAMES_COUNTRIES_DEST, COUNTRIES.manifest)
    fetch(CLDR_CURRENCY_DATA_URL, CLDR_CURRENCY_DATA_PATH, COUNTRIES.manifest)
