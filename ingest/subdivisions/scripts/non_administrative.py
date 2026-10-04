from ingest.utils import ingest_log
from ingest.shared.models import SubdivisionModel
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap, GroupingTwinOrphan
from .automerge import merge_matched_sub


def _twin(grouping: SubdivisionModel, sub_map: SubdivisionMap) -> SubdivisionModel | None:
    """The unclaimed GeoNames level-1 record every already-merged child of the grouping sits under, if there is one."""
    child_codes = [
        sub.geonames_code for sub in sub_map.filter(grouping.country.alpha2)
        if sub.parent_iso_code == grouping.iso_code and sub.geonames_code is not None
    ]
    # a child merged into a level-1 record means GeoNames' level 1 is the children's tier, not the grouping's
    if not child_codes or any(code.count(".") != 2 for code in child_codes):
        return None
    parent_codes = {code.rsplit(".", 1)[0] for code in child_codes}
    if len(parent_codes) != 1:
        return None
    twin = sub_map.get(geo_code=parent_codes.pop())
    if twin is None or twin.iso_code is not None:
        return None
    return twin


def apply_non_administrative(
    non_administrative_subs: list[SubdivisionModel],
    sub_map: SubdivisionMap,
    resolution_map: ResolutionMap,
) -> None:
    """Merges each non-administrative grouping into its GeoNames twin when one exists, otherwise adds it as-is, recording either in automerge.bypassed."""
    resolution_map.automerge.bypassed = {}
    for grouping in non_administrative_subs:
        assert grouping.iso_code is not None
        twin = _twin(grouping, sub_map)
        if twin is None:
            sub_map.add(grouping)
            resolution_map.automerge.bypassed[grouping.iso_code] = None
            continue
        ingest_log.writeline(f"bypassed {grouping.iso_code} '{grouping.name}' merged into its GeoNames twin {twin.geonames_code} '{twin.name}'")
        merge_matched_sub(grouping, twin)
        resolution_map.automerge.bypassed[grouping.iso_code] = twin.geonames_id

    twinned = sum(1 for geonames_id in resolution_map.automerge.bypassed.values() if geonames_id is not None)
    ingest_log.writeline(
        f"bypassed {len(non_administrative_subs)} subdivisions as non-administrative, {twinned} merged into a GeoNames twin"
    )


def flag_grouping_twin_merges(
    non_administrative_subs: list[SubdivisionModel],
    sub_map: SubdivisionMap,
    resolution_map: ResolutionMap,
) -> None:
    """Sends an automerge result to review as a grouping_twin orphan when it merged a grouping's child into a level-1 record that the child's merged siblings sit under, i.e. into the grouping's own twin."""
    resolution_map.automerge.orphans.grouping_twin = []
    groupings = {grouping.iso_code for grouping in non_administrative_subs}
    for iso_code, match in list(resolution_map.automerge.resolutions.items()):
        target = sub_map.get(geonames_id=match.id)
        if target is None or target.parent_iso_code not in groupings or target.geonames_code is None or target.geonames_code.count(".") != 1:
            continue
        siblings_beneath = [
            sub for sub in sub_map.filter(target.country.alpha2)
            if sub is not target and sub.parent_iso_code == target.parent_iso_code and sub.geonames_code is not None
            and sub.geonames_code.startswith(target.geonames_code + ".")
        ]
        if not siblings_beneath:
            continue
        ingest_log.writeline(
            f"{iso_code} merged into {target.geonames_code}, which its siblings under non-administrative {target.parent_iso_code} sit beneath, so it is likely the grouping's twin; sent for review",
            level="WARN",
        )
        del resolution_map.automerge.resolutions[iso_code]
        resolution_map.automerge.orphans.grouping_twin.append(
            GroupingTwinOrphan(iso_code=iso_code, candidate_geonames_id=match.id)
        )
