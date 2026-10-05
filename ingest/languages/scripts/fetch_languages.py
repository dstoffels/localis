from ingest.utils import LANGUAGES, cldr_url, fetch, iso_codes_url

ISO_LANGUAGES_PATH = LANGUAGES.inputs / "iso_639-3.json"
CLDR_LANGUAGE_NAMES_PATH = LANGUAGES.inputs / "cldr_language_names_en.json"
CLDR_LANGUAGE_DATA_PATH = LANGUAGES.inputs / "cldr_language_data.json"


def fetch_languages_sources() -> None:
    """Downloads whichever of ISO 639-3, CLDR's English language names and CLDR's language data changed."""
    fetch(iso_codes_url(ISO_LANGUAGES_PATH.name), ISO_LANGUAGES_PATH, LANGUAGES.manifest)
    fetch(cldr_url("cldr-localenames-full/main/en/languages.json"), CLDR_LANGUAGE_NAMES_PATH, LANGUAGES.manifest)
    fetch(cldr_url("cldr-core/supplemental/languageData.json"), CLDR_LANGUAGE_DATA_PATH, LANGUAGES.manifest)
