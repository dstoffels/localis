from ingest.utils import MACROREGIONS, fetch

CLDR_JSON_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json"

CLDR_TERRITORY_CONTAINMENT_URL = f"{CLDR_JSON_URL}/cldr-core/supplemental/territoryContainment.json"
CLDR_TERRITORY_CONTAINMENT_PATH = MACROREGIONS.inputs / "cldr_territory_containment.json"

CLDR_TERRITORY_NAMES_URL = f"{CLDR_JSON_URL}/cldr-localenames-full/main/en/territories.json"
CLDR_TERRITORY_NAMES_PATH = MACROREGIONS.inputs / "cldr_territory_names_en.json"


def fetch_macroregions_sources() -> None:
    """Downloads whichever of CLDR's territory containment and English territory names changed."""
    fetch(CLDR_TERRITORY_CONTAINMENT_URL, CLDR_TERRITORY_CONTAINMENT_PATH, MACROREGIONS.manifest)
    fetch(CLDR_TERRITORY_NAMES_URL, CLDR_TERRITORY_NAMES_PATH, MACROREGIONS.manifest)
