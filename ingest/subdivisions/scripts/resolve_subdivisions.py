from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.utils import ingest_log
import json
from .merge_subdivisions import merge_matched_sub
from ingest.shared.models import SubdivisionModel


def _apply_cached_resolutions(
    unmerged_iso_subs: list[SubdivisionModel],
    resolution_map: dict[str, int | None],
    submap: SubdivisionMap,
) -> list[SubdivisionModel]:
    """Re-apply cached resolutions to a list of unmatched ISO subdivisions."""
    still_unmerged: list[SubdivisionModel] = []
    for iso_sub in unmerged_iso_subs:
        if not _apply_cached_resolution(iso_sub, resolution_map, submap):
            still_unmerged.append(iso_sub)
    return still_unmerged


def _apply_cached_resolution(
    iso_sub: SubdivisionModel,
    resolution_map: dict[str, int | None],
    submap: SubdivisionMap,
) -> bool:
    """Re-apply a previously recorded decision for iso_sub, if one exists. Returns True if applied.
    A geonames_id of None means "add as-is"; absence from the map means no cached decision exists."""
    if iso_sub.iso_code not in resolution_map:
        return False

    geonames_id = resolution_map[iso_sub.iso_code]

    if geonames_id is None:
        submap.add(iso_sub)
        return True

    mapped_sub = submap.get(geonames_id=geonames_id)
    if mapped_sub:
        if mapped_sub.iso_code and mapped_sub.iso_code != iso_sub.iso_code:
            ingest_log.writeline(
                f"cached resolution conflict: {iso_sub.iso_code} '{iso_sub.name}'s target {mapped_sub.geonames_code} '{mapped_sub.name}' was already auto-merged with {mapped_sub.iso_code}, falling back to orphan resolution",
                level="WARN",
            )
            return False
        merge_matched_sub(iso_sub, mapped_sub)
        return True

    ingest_log.writeline(
        f"stale geonames_id reference: {geonames_id} (iso_code {iso_sub.iso_code} '{iso_sub.name}') not found in current subdivision map",
        level="WARN",
    )
    return False


def dump_orphans(orphaned_subs: list[SubdivisionModel]) -> None:
    if orphaned_subs:
        payload = {}

        for iso_sub in orphaned_subs:
            payload[iso_sub.iso_code] = {
                "name": iso_sub.name,
                "aliases": iso_sub.aliases,
                "country": iso_sub.country.name,
                "type": iso_sub.type,
            }

        (SUBDIVISIONS_OUTPUTS_PATH / "orphaned_subdivisions.json").write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )


def resolve_unmerged_subs(
    unmerged_iso_subs: list[SubdivisionModel],
    submap: SubdivisionMap,
) -> None:
    """Applies cached resolutions and dumps whatever's left to orphaned_subdivisions.json
    for the resolve-subdivisions skill to resolve."""
    resolution_map_path = SUBDIVISIONS_OUTPUTS_PATH / "resolution_map.json"
    if not resolution_map_path.exists():
        resolution_map_path.write_text("{}", encoding="utf-8")

    resolution_map: dict[str, int | None] = (
        json.loads(resolution_map_path.read_text(encoding="utf-8")) or {}
    )

    before = len(unmerged_iso_subs)
    orphaned = _apply_cached_resolutions(unmerged_iso_subs, resolution_map, submap)
    ingest_log.writeline(
        f"resolved {before - len(orphaned)}/{before} unmerged subdivisions from cached resolutions"
    )

    ingest_log.writeline(f"{len(orphaned)} subdivisions orphaned, pending manual resolution")
    dump_orphans(orphaned)
