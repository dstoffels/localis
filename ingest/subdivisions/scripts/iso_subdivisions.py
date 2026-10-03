from ingest.utils import SUBDIVISIONS_INPUTS_PATH, ingest_log
from ingest.shared.models import CountryModel
from ingest.shared.models import SubdivisionModel
from ingest.subdivisions.utils.resolution_map import ResolutionMap
import json
import re

_TRAILING_BRACKET_RE = re.compile(r"^(.*?)\s*[\[\(]([^\[\]\(\)]+)[\]\)]\s*$")
_TRAILING_CODE_RE = re.compile(r"\s+[A-Z]{2,3}-[A-Z0-9]{1,6}$")
_BARE_CODE_RE = re.compile(r"^[A-Z]{2,3}-[A-Z0-9]{1,6}$")
_NON_NAME_BRACKET_CONTENT = {"city", "partial", "eh", "eh-partial"}


def _split_bracketed_name(raw_name: str) -> tuple[str, str | None]:
    """iso-codes suffixes some names with "[Content]"/"(Content)": a genuine alternate name (kept as an alias), a bare subdivision code, or a territory-dispute annotation (both discarded)."""
    match = _TRAILING_BRACKET_RE.match(raw_name)
    if not match:
        return raw_name, None

    primary, content = match.group(1).strip(), match.group(2).strip()
    content = _TRAILING_CODE_RE.sub("", content).strip()

    if not content or content.lower() in _NON_NAME_BRACKET_CONTENT:
        return primary, None
    if content.lower() == primary.lower():
        return primary, None
    if _BARE_CODE_RE.match(content):
        return primary, None

    return primary, content


def _admin_level(entry: dict, entries_by_code: dict[str, dict], resolution_map: ResolutionMap) -> int:
    """Depth of `entry` in its real (non-bypassed) ISO parent chain: 0 if non-administrative itself, otherwise 1 plus one for every ancestor up the chain that isn't non-administrative. A non-administrative ancestor is transparent: it neither counts toward depth nor stops the climb from continuing past it."""
    alpha2 = entry["code"].split("-")[0]
    if resolution_map.is_non_administrative(alpha2, entry["type"]):
        return 0

    depth = 1
    parent_code = entry.get("parent")
    while parent_code:
        parent_entry = entries_by_code.get(parent_code)
        if parent_entry is None:
            break
        if not resolution_map.is_non_administrative(alpha2, parent_entry["type"]):
            depth += 1
        parent_code = parent_entry.get("parent")

    return depth


def load_iso_subs(
    countries: dict[str, CountryModel],
    resolution_map: ResolutionMap,
) -> tuple[dict[str, SubdivisionModel], list[SubdivisionModel]]:
    """Parses ISO 3166-2 subdivisions from Debian's iso-codes, the authoritative source. Returns (iso_subs, non_administrative_subs), the latter resolved separately by apply_non_administrative()."""
    ingest_log.writeline("Loading ISO subdivisions...")
    iso_subs: dict[str, SubdivisionModel] = {}
    non_administrative_subs: list[SubdivisionModel] = []

    with open(SUBDIVISIONS_INPUTS_PATH / "iso_3166-2.json", "r", encoding="utf-8") as f:
        entries: list[dict] = json.load(f)["3166-2"]

    entries_by_code = {entry["code"]: entry for entry in entries}

    for entry in entries:
        iso_code = entry["code"]
        alpha2 = iso_code.split("-")[0]
        parent_iso_code = entry.get("parent")
        admin_level = _admin_level(entry, entries_by_code, resolution_map)

        country = countries.get(alpha2)
        if not country:
            raise ValueError(f"Country not found for alpha2: {alpha2}")

        name, bracket_alias = _split_bracketed_name(entry["name"])

        subdivision = SubdivisionModel(
            id=0,  # temporary, will be set when all loaded
            name=name,
            country=country,
            type=entry["type"],
            iso_code=iso_code,
            admin_level=admin_level,
            aliases=[bracket_alias] if bracket_alias else [],
            geonames_code=None,  # may be set later if merged with GeoNames subdivision
            geonames_id=None,  # may be set later if merged with GeoNames subdivision
            parent=parent_iso_code,  # temporarily set to iso_code string to map later once all iso subs are loaded
        )

        # set temporary id to hashid for later mapping
        subdivision.set_hashid()
        assert subdivision.hashid is not None
        subdivision.id = subdivision.hashid

        if admin_level == 0:
            non_administrative_subs.append(subdivision)
        else:
            iso_subs[iso_code] = subdivision

    # parent stays as the raw iso_code string here; SubdivisionMap.refresh()
    # resolves it to the actual object once merging/resolution has settled,
    # since the object it should point to may be discarded during merge.
    return iso_subs, non_administrative_subs
