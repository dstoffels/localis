from data.utils import has_changed, download
from data.paths import CITIES_RAW_PATH, CITIES_MANIFEST_PATH, GEONAMES_DUMP_URL
import zipfile


def fetch_cities_sources() -> bool:
    cities_url = f"{GEONAMES_DUMP_URL}/allCountries.zip"
    zip_dest = CITIES_RAW_PATH / "allCountries.zip"

    if not has_changed(cities_url, zip_dest, CITIES_MANIFEST_PATH):
        return False

    download(cities_url, zip_dest, CITIES_MANIFEST_PATH)

    with zipfile.ZipFile(zip_dest) as zf:
        zf.extract("allCountries.txt", CITIES_RAW_PATH)

    zip_dest.unlink()

    return True
