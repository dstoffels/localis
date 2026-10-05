import json
from dataclasses import dataclass
from ingest.shared.models import MacroregionModel, MacroregionType
from ingest.utils import ingest_log
from .fetch_macroregions import CLDR_TERRITORY_CONTAINMENT_PATH, CLDR_TERRITORY_NAMES_PATH

WORLD = "001"
GROUPING_SUFFIX = "-status-grouping"
DEPRECATED_SUFFIX = "-status-deprecated"


@dataclass
class Macroregions:
    """CLDR's macroregions and where each territory sits among them."""

    all: list[MacroregionModel]
    # territory code -> its subregion in CLDR's main tree
    subregion_of: dict[str, MacroregionModel]
    # withdrawn territory code -> the subregions CLDR keeps it in under deprecated status
    deprecated_subregions_of: dict[str, list[MacroregionModel]]
    # territory code -> the groupings it belongs to
    groupings_of: dict[str, list[MacroregionModel]]


def load_macroregions() -> Macroregions:
    """Builds CLDR's regions, subregions and groupings from its territory containment, named from its English territory names."""
    ingest_log.writeline("Loading CLDR macroregions...")
    containment: dict[str, dict] = json.loads(CLDR_TERRITORY_CONTAINMENT_PATH.read_text(encoding="utf-8"))["supplemental"]["territoryContainment"]
    names: dict[str, str] = json.loads(CLDR_TERRITORY_NAMES_PATH.read_text(encoding="utf-8"))["main"]["en"]["localeDisplayNames"]["territories"]

    def contains(code: str) -> list[str]:
        return containment.get(code, {}).get("_contains", [])

    # the main tree is every plain entry; "-status-grouping" entries place the groupings, "-status-deprecated" ones hold withdrawn codes
    tree = {code: entry["_contains"] for code, entry in containment.items() if "-status-" not in code and entry.get("_grouping") != "true"}
    region_codes = sorted(contains(WORLD))
    subregion_codes = sorted(code for region in region_codes for code in contains(region))
    grouping_codes = sorted(code for code, entry in containment.items() if entry.get("_grouping") == "true")

    for code in subregion_codes:
        if code not in tree:
            raise ValueError(f"CLDR region child {code} isn't a subregion in the containment tree")

    by_code: dict[str, MacroregionModel] = {}

    def add(code: str, type_: MacroregionType, parent: MacroregionModel | None) -> None:
        if code not in names:
            raise ValueError(f"CLDR has no English name for macroregion {code}")
        by_code[code] = MacroregionModel(name=names[code], code=code, type=type_, parent=parent)

    for code in region_codes:
        add(code, "region", None)
    for region in region_codes:
        for code in sorted(contains(region)):
            add(code, "subregion", by_code[region])
    # a grouping's parent is the region CLDR files it under; groupings filed under World (EU, euro area, UN) span regions and have none
    grouping_parent = {code: parent for parent in region_codes for code in contains(parent + GROUPING_SUFFIX)}
    for code in grouping_codes:
        parent = grouping_parent.get(code)
        add(code, "grouping", by_code[parent] if parent else None)

    subregion_of: dict[str, MacroregionModel] = {}
    for code in subregion_codes:
        for territory in contains(code):
            if territory in subregion_of:
                raise ValueError(f"CLDR places {territory} in both {subregion_of[territory].code} and {code}")
            subregion_of[territory] = by_code[code]

    deprecated_subregions_of: dict[str, list[MacroregionModel]] = {}
    for key in containment:
        if key.endswith(DEPRECATED_SUFFIX) and key.removesuffix(DEPRECATED_SUFFIX) in subregion_codes:
            for territory in contains(key):
                deprecated_subregions_of.setdefault(territory, []).append(by_code[key.removesuffix(DEPRECATED_SUFFIX)])

    groupings_of: dict[str, list[MacroregionModel]] = {}
    for code in grouping_codes:
        # a grouping lists subregions (Latin America) or territories directly (EU)
        members = [t for member in contains(code) for t in (contains(member) if member in subregion_codes else [member])]
        for territory in members:
            groupings_of.setdefault(territory, []).append(by_code[code])

    macroregions = list(by_code.values())
    ingest_log.writeline(
        f"{len(region_codes)} regions, {len(subregion_codes)} subregions and {len(grouping_codes)} groupings; {len(subregion_of)} territories placed"
    )
    return Macroregions(macroregions, subregion_of, deprecated_subregions_of, groupings_of)
