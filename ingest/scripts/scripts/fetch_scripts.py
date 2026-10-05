from ingest.utils import SCRIPTS, cldr_url, fetch, iso_codes_url

ISO_SCRIPTS_PATH = SCRIPTS.inputs / "iso_15924.json"
CLDR_SCRIPT_NAMES_PATH = SCRIPTS.inputs / "cldr_script_names_en.json"


def fetch_scripts_sources() -> None:
    """Downloads whichever of ISO 15924 and CLDR's English script names changed."""
    fetch(iso_codes_url(ISO_SCRIPTS_PATH.name), ISO_SCRIPTS_PATH, SCRIPTS.manifest)
    fetch(cldr_url("cldr-localenames-full/main/en/scripts.json"), CLDR_SCRIPT_NAMES_PATH, SCRIPTS.manifest)
