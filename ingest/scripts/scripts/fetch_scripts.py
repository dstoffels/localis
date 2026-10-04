from ingest.utils import fetch
from ingest.utils import SCRIPTS_INPUTS_PATH, SCRIPTS_MANIFEST_PATH

ISO_SCRIPTS_URL = "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_15924.json"
ISO_SCRIPTS_PATH = SCRIPTS_INPUTS_PATH / "iso_15924.json"
CLDR_SCRIPT_NAMES_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json/cldr-localenames-full/main/en/scripts.json"
CLDR_SCRIPT_NAMES_PATH = SCRIPTS_INPUTS_PATH / "cldr_script_names_en.json"


def fetch_scripts_sources(force: bool = False) -> bool:
    """Downloads whichever of ISO 15924 and CLDR's English script names changed; True if the stage should rebuild."""
    fetched = [
        fetch(ISO_SCRIPTS_URL, ISO_SCRIPTS_PATH, SCRIPTS_MANIFEST_PATH),
        fetch(CLDR_SCRIPT_NAMES_URL, CLDR_SCRIPT_NAMES_PATH, SCRIPTS_MANIFEST_PATH),
    ]
    return any(fetched) or force
