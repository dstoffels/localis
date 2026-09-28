from data.utils import download
from data.paths import CITIES_RAW_PATH, CITIES_MANIFEST_PATH, GEONAMES_DUMP_URL
import zipfile


def fetch_cities_sources() -> bool:
    cities_url = f"{GEONAMES_DUMP_URL}/allCountries.zip"
    zip_dest = CITIES_RAW_PATH / "allCountries.zip"
    changed = download(cities_url, zip_dest, CITIES_MANIFEST_PATH)

    if changed:
        with zipfile.ZipFile(zip_dest) as zf:
            zf.extract("allCountries.txt", CITIES_RAW_PATH)

        zip_dest.unlink()

    return changed
