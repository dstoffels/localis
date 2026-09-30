from ingest.utils import has_changed, download
from ingest.utils import SHARED_INPUTS_PATH, SHARED_MANIFEST_PATH, GEONAMES_DUMP_URL
import zipfile

ALT_NAMES_URL = f"{GEONAMES_DUMP_URL}/alternateNamesV2.zip"
ALT_NAMES_ZIP_PATH = SHARED_INPUTS_PATH / "alternateNamesV2.zip"
ALT_NAMES_PATH = SHARED_INPUTS_PATH / "alternateNamesV2.txt"


def fetch_shared_sources(force: bool = False) -> bool:
    should_download = has_changed(ALT_NAMES_URL, ALT_NAMES_ZIP_PATH, SHARED_MANIFEST_PATH)

    if not should_download and not force:
        return False

    if should_download:
        download(ALT_NAMES_URL, ALT_NAMES_ZIP_PATH, SHARED_MANIFEST_PATH)

        with zipfile.ZipFile(ALT_NAMES_ZIP_PATH) as zf:
            zf.extract("alternateNamesV2.txt", SHARED_INPUTS_PATH)

        ALT_NAMES_ZIP_PATH.unlink()

    return True
