from data.utils import CITIES_RAW_PATH, download, GEONAMES_DUMP_URL
import zipfile


def fetch_cities_sources() -> None:
    zip_dest = CITIES_RAW_PATH / "allCountries.zip"
    download(f"{GEONAMES_DUMP_URL}/allCountries.zip", zip_dest)

    with zipfile.ZipFile(zip_dest) as zf:
        zf.extract("allCountries.txt", CITIES_RAW_PATH)

    zip_dest.unlink()
