import json
from .fetch_shared import CLDR_TERRITORY_INFO_PATH

OFFICIAL_STATUSES = {"official", "official_regional", "de_facto_official"}


def load_cldr_territory_languages() -> dict[str, set[str]]:
    """Map each territory's alpha2 code to its set of official language base codes, from CLDR's territoryInfo.json."""
    data = json.loads(CLDR_TERRITORY_INFO_PATH.read_text(encoding="utf-8"))
    territory_info = data["supplemental"]["territoryInfo"]

    territory_languages: dict[str, set[str]] = {}
    for alpha2, info in territory_info.items():
        languages = {
            lang_code.split("_")[0].split("-")[0]
            for lang_code, lang_info in info.get("languagePopulation", {}).items()
            if lang_info.get("_officialStatus") in OFFICIAL_STATUSES
        }
        if languages:
            territory_languages[alpha2] = languages

    return territory_languages
