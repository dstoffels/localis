from ingest.utils import LANGUAGES, fetch

ISO_LANGUAGES_URL = "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_639-3.json"
ISO_LANGUAGES_PATH = LANGUAGES.inputs / "iso_639-3.json"
CLDR_JSON_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json"
CLDR_LANGUAGE_NAMES_URL = f"{CLDR_JSON_URL}/cldr-localenames-full/main/en/languages.json"
CLDR_LANGUAGE_NAMES_PATH = LANGUAGES.inputs / "cldr_language_names_en.json"
CLDR_LANGUAGE_DATA_URL = f"{CLDR_JSON_URL}/cldr-core/supplemental/languageData.json"
CLDR_LANGUAGE_DATA_PATH = LANGUAGES.inputs / "cldr_language_data.json"


def fetch_languages_sources() -> None:
    """Downloads whichever of ISO 639-3, CLDR's English language names and CLDR's language data changed."""
    fetch(ISO_LANGUAGES_URL, ISO_LANGUAGES_PATH, LANGUAGES.manifest)
    fetch(CLDR_LANGUAGE_NAMES_URL, CLDR_LANGUAGE_NAMES_PATH, LANGUAGES.manifest)
    fetch(CLDR_LANGUAGE_DATA_URL, CLDR_LANGUAGE_DATA_PATH, LANGUAGES.manifest)
