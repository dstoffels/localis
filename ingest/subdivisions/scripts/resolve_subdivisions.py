from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.utils import ingest_log
from .merge_subdivisions import merge_matched_sub
from ingest.shared.models import SubdivisionModel


def apply_skill_resolved(
    iso_subs: dict[str, SubdivisionModel],
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
) -> dict[str, SubdivisionModel]:
    """Applies every skill-resolved decision directly, before try_merge ever sees these iso_subs, so a verified human decision can never lose its target to a fresh auto-merge. Returns the remaining iso_subs that still need auto-merging."""
    remaining: dict[str, SubdivisionModel] = {}
    for iso_code, iso_sub in iso_subs.items():
        if iso_code not in resolution_map.skill_resolved:
            remaining[iso_code] = iso_sub
            continue
        if not _apply_skill_resolution(iso_sub, resolution_map, sub_map):
            remaining[iso_code] = iso_sub

    resolved_count = len(iso_subs) - len(remaining)
    ingest_log.writeline(
        f"resolved {resolved_count}/{len(iso_subs)} subdivisions from skill-resolved decisions"
    )
    return remaining


def _apply_skill_resolution(
    iso_sub: SubdivisionModel,
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
) -> bool:
    """Applies a single skill-resolved decision. Returns True if applied. A geonames_id of None means "add as-is"."""
    geonames_id = resolution_map.skill_resolved[iso_sub.iso_code]

    if geonames_id is None:
        sub_map.add(iso_sub)
        return True

    mapped_sub = sub_map.get(geonames_id=geonames_id)
    if mapped_sub is None:
        ingest_log.writeline(
            f"stale geonames_id reference: {geonames_id} (iso_code {iso_sub.iso_code} '{iso_sub.name}') not found in current subdivision map",
            level="WARN",
        )
        return False

    if mapped_sub.iso_code and mapped_sub.iso_code != iso_sub.iso_code:
        ingest_log.writeline(
            f"skill-resolved conflict: {iso_sub.iso_code} '{iso_sub.name}'s target {mapped_sub.geonames_code} '{mapped_sub.name}' is already claimed by {mapped_sub.iso_code}",
            level="WARN",
        )
        return False

    merge_matched_sub(iso_sub, mapped_sub)
    return True
