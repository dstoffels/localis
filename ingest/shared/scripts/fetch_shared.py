from ingest.utils import has_changed, download
from ingest.utils import SHARED_INPUTS_PATH, SHARED_MANIFEST_PATH, GEONAMES_DUMP_URL
import zipfile

ALT_NAMES_URL = f"{GEONAMES_DUMP_URL}/alternateNamesV2.zip"
ALT_NAMES_ZIP_PATH = SHARED_INPUTS_PATH / "alternateNamesV2.zip"
ALT_NAMES_PATH = SHARED_INPUTS_PATH / "alternateNamesV2.txt"

CLDR_TERRITORY_INFO_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-core/supplemental/territoryInfo.json"
CLDR_TERRITORY_INFO_PATH = SHARED_INPUTS_PATH / "cldr_territory_info.json"


def fetch_shared_sources(force: bool = False) -> bool:
    # Check first: if either source changed, we need both files locally, so a
    # partial fetch would leave the other missing.
    should_download = any(
        [
            has_changed(
                ALT_NAMES_URL,
                ALT_NAMES_ZIP_PATH,
                SHARED_MANIFEST_PATH,
                exists_path=ALT_NAMES_PATH,
            ),
            has_changed(
                CLDR_TERRITORY_INFO_URL, CLDR_TERRITORY_INFO_PATH, SHARED_MANIFEST_PATH
            ),
        ]
    )

    if not should_download and not force:
        return False

    if should_download:
        download(ALT_NAMES_URL, ALT_NAMES_ZIP_PATH, SHARED_MANIFEST_PATH)

        with zipfile.ZipFile(ALT_NAMES_ZIP_PATH) as zf:
            zf.extract("alternateNamesV2.txt", SHARED_INPUTS_PATH)

        ALT_NAMES_ZIP_PATH.unlink()

        download(
            CLDR_TERRITORY_INFO_URL, CLDR_TERRITORY_INFO_PATH, SHARED_MANIFEST_PATH
        )

    return True
