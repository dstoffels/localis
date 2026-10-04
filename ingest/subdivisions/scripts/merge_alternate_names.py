import re
from ingest.utils import ingest_log
from ingest.shared.scripts.fetch_shared import ALT_NAMES_PATH
from ingest.shared.scripts.cldr import load_cldr_territory_languages
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.utils.strings import dedupe
from localis.utils.strings import is_latin
from ingest.shared.models import SubdivisionModel

# isolanguage values that aren't actual human-language name variants and should never be treated as candidate name text
NON_NAME_LANG_CODES = {"wkdt", "link", "post", "iata", "icao", "faac", "abbr"}

# invisible bidi/formatting control characters sometimes embedded literally in RTL-script alternate names pulled from Wikipedia/Wikidata
BIDI_CONTROL_CHARS = re.compile("[​-\u200F\u202A-\u202E\u2066-\u2069]")


def _strip_bidi_controls(name: str) -> str:
    return BIDI_CONTROL_CHARS.sub("", name)


def merge_alternate_name_aliases(sub_map: SubdivisionMap) -> None:
    """Enrich each GeoNames subdivision's aliases with its English and country-official-language alternate names from GeoNames' alternateNamesV2 dump."""
    ingest_log.writeline("Merging GeoNames alternate names into subdivision aliases...")
    territory_languages = load_cldr_territory_languages()
    touched: dict[int, SubdivisionModel] = {}

    with open(ALT_NAMES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            # alternateNameId, geonameid, isolanguage, alternate name, isPreferredName, isShortName, isColloquial, isHistoric, from, to
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 4:
                continue

            geonames_id_raw = parts[1]
            if not geonames_id_raw.isdigit():
                continue

            sub = sub_map.get(geonames_id=int(geonames_id_raw))
            if sub is None:
                continue

            isolanguage = parts[2]
            if isolanguage in NON_NAME_LANG_CODES:
                continue

            allowed_languages = {"en"} | territory_languages.get(
                sub.country.alpha2, set()
            )
            if isolanguage not in allowed_languages:
                continue

            name = _strip_bidi_controls(parts[3])
            # only Latin-script names ship; names in other scripts are left to localized names
            if not name or name == sub.name or not is_latin(name):
                continue

            is_colloquial = len(parts) > 6 and parts[6] == "1"
            is_historic = len(parts) > 7 and parts[7] == "1"
            if is_historic or is_colloquial:
                continue

            sub.aliases.append(name)
            assert sub.geonames_id is not None
            touched[sub.geonames_id] = sub

    for sub in touched.values():
        sub.aliases = dedupe(sub.aliases)

    ingest_log.writeline(f"Enriched {len(touched)} GeoNames subdivisions with alternate names")
