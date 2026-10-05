from ingest.utils import MACROREGIONS, cldr_url, fetch

CLDR_TERRITORY_CONTAINMENT_PATH = MACROREGIONS.inputs / "cldr_territory_containment.json"

CLDR_TERRITORY_NAMES_PATH = MACROREGIONS.inputs / "cldr_territory_names_en.json"


def fetch_macroregions_sources() -> None:
    """Downloads whichever of CLDR's territory containment and English territory names changed."""
    fetch(cldr_url("cldr-core/supplemental/territoryContainment.json"), CLDR_TERRITORY_CONTAINMENT_PATH, MACROREGIONS.manifest)
    fetch(cldr_url("cldr-localenames-full/main/en/territories.json"), CLDR_TERRITORY_NAMES_PATH, MACROREGIONS.manifest)
