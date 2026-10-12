from ingest.utils import COUNTRIES, GEONAMES_DUMP_URL, cldr_url, fetch, iso_codes_url

ISO_COUNTRIES_PATH = COUNTRIES.inputs / "iso_3166-1.json"
ISO_HISTORIC_COUNTRIES_PATH = COUNTRIES.inputs / "iso_3166-3.json"
GEONAMES_COUNTRIES_URL = f"{GEONAMES_DUMP_URL}/countryInfo.txt"
GEONAMES_COUNTRIES_DEST = COUNTRIES.inputs / "geonamesInfo.txt"
# the dump's readme, the only place GeoNames publishes its continent codes' names and geonameIds
GEONAMES_README_URL = f"{GEONAMES_DUMP_URL}/readme.txt"
GEONAMES_README_DEST = COUNTRIES.inputs / "geonames_readme.txt"
CLDR_CURRENCY_DATA_PATH = COUNTRIES.inputs / "cldr_currency_data.json"


def fetch_countries_sources() -> None:
    """Downloads whichever of ISO 3166-1, ISO 3166-3, GeoNames' country info and readme and CLDR's currency data changed."""
    fetch(iso_codes_url(ISO_COUNTRIES_PATH.name), ISO_COUNTRIES_PATH, COUNTRIES.manifest)
    fetch(iso_codes_url(ISO_HISTORIC_COUNTRIES_PATH.name), ISO_HISTORIC_COUNTRIES_PATH, COUNTRIES.manifest)
    fetch(GEONAMES_COUNTRIES_URL, GEONAMES_COUNTRIES_DEST, COUNTRIES.manifest)
    fetch(GEONAMES_README_URL, GEONAMES_README_DEST, COUNTRIES.manifest)
    fetch(cldr_url("cldr-core/supplemental/currencyData.json"), CLDR_CURRENCY_DATA_PATH, COUNTRIES.manifest)
