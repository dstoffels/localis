from ingest.utils import has_changed, download
from ingest.utils import MACROREGIONS_INPUTS_PATH, MACROREGIONS_MANIFEST_PATH

CLDR_JSON_URL = "https://raw.githubusercontent.com/unicode-org/cldr-json/main/cldr-json"

CLDR_TERRITORY_CONTAINMENT_URL = f"{CLDR_JSON_URL}/cldr-core/supplemental/territoryContainment.json"
CLDR_TERRITORY_CONTAINMENT_PATH = MACROREGIONS_INPUTS_PATH / "cldr_territory_containment.json"

CLDR_TERRITORY_NAMES_URL = f"{CLDR_JSON_URL}/cldr-localenames-full/main/en/territories.json"
CLDR_TERRITORY_NAMES_PATH = MACROREGIONS_INPUTS_PATH / "cldr_territory_names_en.json"


def fetch_macroregions_sources(force: bool = False) -> bool:
    """Downloads CLDR's territory containment and English territory names when either changed; True if the stage should rebuild."""
    # check both first: building the macroregions needs both files, so a partial fetch would leave them out of step
    should_download = any(
        [
            has_changed(CLDR_TERRITORY_CONTAINMENT_URL, CLDR_TERRITORY_CONTAINMENT_PATH, MACROREGIONS_MANIFEST_PATH),
            has_changed(CLDR_TERRITORY_NAMES_URL, CLDR_TERRITORY_NAMES_PATH, MACROREGIONS_MANIFEST_PATH),
        ]
    )

    if not should_download and not force:
        return False

    if should_download:
        download(CLDR_TERRITORY_CONTAINMENT_URL, CLDR_TERRITORY_CONTAINMENT_PATH, MACROREGIONS_MANIFEST_PATH)
        download(CLDR_TERRITORY_NAMES_URL, CLDR_TERRITORY_NAMES_PATH, MACROREGIONS_MANIFEST_PATH)

    return True
