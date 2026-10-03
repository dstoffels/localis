from ingest.utils import has_changed, download
from ingest.utils import CITIES_INPUTS_PATH, CITIES_MANIFEST_PATH, GEONAMES_DUMP_URL
import zipfile


def fetch_cities_sources(force: bool = False) -> bool:
    cities_url = f"{GEONAMES_DUMP_URL}/cities500.zip"
    zip_dest = CITIES_INPUTS_PATH / "cities500.zip"
    txt_dest = CITIES_INPUTS_PATH / "cities500.txt"

    should_download = has_changed(
        cities_url, zip_dest, CITIES_MANIFEST_PATH, exists_path=txt_dest
    )

    if not should_download and not force:
        return False

    if should_download:
        download(cities_url, zip_dest, CITIES_MANIFEST_PATH)

        with zipfile.ZipFile(zip_dest) as zf:
            zf.extract("cities500.txt", CITIES_INPUTS_PATH)

        zip_dest.unlink()

    return True
