import functools
import json
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.shared.models import SubdivisionModel
from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH
from ingest.shared.scripts import load_countries
from ingest.subdivisions.scripts import (
    load_iso_subs,
    merge_ipregistry_aliases,
    map_geonames_subdivisions,
    merge_alternate_name_aliases,
    candidate_pool,
    score_candidates,
)

RESOLUTION_MAP_PATH = SUBDIVISIONS_OUTPUTS_PATH / "resolution_map.json"
RESOLUTION_LOG_PATH = SUBDIVISIONS_OUTPUTS_PATH / "resolution_log.txt"
REVIEW_OUTPUT_PATH = SUBDIVISIONS_OUTPUTS_PATH / "review_output.json"


@functools.cache
def _resolution_map() -> ResolutionMap:
    return ResolutionMap.load(RESOLUTION_MAP_PATH)


def write_resolution(iso_code: str, geonames_id: int | None) -> None:
    """geonames_id of None means "add as-is"."""
    resolution_map = _resolution_map()
    resolution_map.skill_resolved[iso_code] = geonames_id
    resolution_map.save(RESOLUTION_MAP_PATH)


@functools.cache
def _countries():
    return load_countries()


def _apply_resolved_claims(sub_map: SubdivisionMap, resolution_map: ResolutionMap) -> None:
    """Marks every GeoNames sub already claimed by a recorded resolution, so a target another iso_code already has doesn't look unclaimed."""
    for source in (resolution_map.skill_resolved, resolution_map.wikidata_merge):
        for iso_code, geonames_id in source.items():
            if geonames_id is None:
                continue
            sub = sub_map.get(geonames_id=geonames_id)
            if sub is not None:
                sub.iso_code = iso_code
    for iso_code, match in resolution_map.auto_merge.resolutions.items():
        sub = sub_map.get(geonames_id=match.id)
        if sub is not None:
            sub.iso_code = iso_code


@functools.cache
def get_geonames_submap() -> SubdivisionMap:
    sub_map = map_geonames_subdivisions(_countries())
    merge_alternate_name_aliases(sub_map)
    _apply_resolved_claims(sub_map, _resolution_map())
    return sub_map


@functools.cache
def _get_iso_subs() -> dict[str, SubdivisionModel]:
    iso_subs, _ = load_iso_subs(_countries(), _resolution_map())
    merge_ipregistry_aliases(iso_subs)
    return iso_subs


def _format_candidate(candidate: SubdivisionModel) -> tuple[int, str]:
    names = ", ".join([candidate.name, *candidate.aliases])
    return (
        candidate.geonames_id,
        f"{names} - [{candidate.admin_level}]",
    )


TOP_TIER_MIN = 10
TOP_TIER_MAX = 100
TOP_TIER_FRACTION = 0.1
BATCH_SIZE = 200


def _get_top_tier_batch_size(pool_size: int) -> int:
    return min(max(TOP_TIER_MIN, round(pool_size * TOP_TIER_FRACTION)), TOP_TIER_MAX)


def _orphan_reason(iso_code: str) -> tuple[str, list[int] | None]:
    """Which orphan bucket iso_code is in, plus its stored close-call candidates if ambiguity."""
    orphans = _resolution_map().auto_merge.orphans
    if iso_code in orphans.no_candidates:
        return "no_candidates", None
    if iso_code in orphans.no_matches:
        return "no_matches", None
    for orphan in orphans.ambiguity:
        if orphan.iso_code == iso_code:
            return "ambiguity", orphan.candidate_geonames_ids
    raise ValueError(f"{iso_code} is not in resolution_map's orphans")


def get_candidates(
    iso_code: str, batch_num: int = 0, return_all: bool = False
) -> dict[int, str]:
    iso_sub: SubdivisionModel | None = _get_iso_subs().get(iso_code, None)
    if not iso_sub:
        raise ValueError(f"{iso_code} is not found in ISO subdivisions")

    reason, candidate_geonames_ids = _orphan_reason(iso_code)
    sub_map = get_geonames_submap()

    # ambiguity's first batch is just try_merge's flagged close-calls, not the full pool
    if reason == "ambiguity" and batch_num == 0 and not return_all:
        close_calls = [sub_map.get(geonames_id=gid) for gid in candidate_geonames_ids]
        return dict(_format_candidate(c) for c in close_calls if c is not None)

    # no_candidates means same-level had nothing; fall back to the whole country
    level = None if reason == "no_candidates" else iso_sub.admin_level
    geo_subs = candidate_pool(sub_map, iso_sub.country.alpha2, level)
    if reason == "ambiguity":
        geo_subs = [g for g in geo_subs if g.geonames_id not in candidate_geonames_ids]
    candidates = [geo_sub for geo_sub, score, needed in score_candidates(iso_sub, geo_subs)]

    if not return_all:
        # ambiguity already used batch 0 for close-calls, so normal pagination restarts at batch 1
        effective_batch_num = batch_num - 1 if reason == "ambiguity" else batch_num
        top_tier_batch_size = _get_top_tier_batch_size(len(candidates))

        if effective_batch_num == 0:
            batch_start, batch_end = 0, top_tier_batch_size
        else:
            batch_start = top_tier_batch_size + (effective_batch_num - 1) * BATCH_SIZE
            batch_end = min(batch_start + BATCH_SIZE, len(candidates))

        if batch_start >= len(candidates):
            return []

        candidates = candidates[batch_start:batch_end]

    return dict(_format_candidate(c) for c in candidates)


def is_valid_candidate(iso_code: str, geo_sub_geonames_id: int) -> tuple[bool, str]:
    """(True, "") if geo_sub_geonames_id belongs to iso_code's own country's candidate pool and hasn't already been claimed by another orphan; otherwise (False, <error message>)."""

    iso_sub = _get_iso_subs().get(iso_code)
    if iso_sub is None:
        return False, "ERROR: Invalid candidate: ISO subdivision not found"

    candidate = get_geonames_submap().get(geonames_id=geo_sub_geonames_id)
    if candidate is None:
        return False, "ERROR: Invalid candidate: not found"

    if candidate.iso_code is not None:
        return (
            False,
            "ERROR: Invalid candidate: already claimed by another ISO subdivision",
        )

    if candidate.country.alpha2 != iso_sub.country.alpha2:
        return False, "ERROR: Invalid candidate: wrong country for this ISO code"

    return True, ""


def get_next_orphan() -> dict | None:
    orphans = _resolution_map().auto_merge.orphans
    ambiguity_codes = [orphan.iso_code for orphan in orphans.ambiguity]
    iso_code = next(
        iter(orphans.no_candidates + orphans.no_matches + ambiguity_codes), None
    )
    if iso_code is None:
        return None

    iso_sub = _get_iso_subs()[iso_code]
    return {
        "iso_code": iso_code,
        "name": iso_sub.name,
        "aliases": iso_sub.aliases,
        "country": iso_sub.country.name,
        "type": iso_sub.type,
    }


def write_orphan_for_review(orphan: dict) -> None:
    """Writes the given orphan to the review output."""
    with open(REVIEW_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(orphan, f, indent=2, ensure_ascii=False)


def log_decision(line: str) -> None:
    with open(RESOLUTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pop_orphan(iso_code: str) -> None:
    """Removes an orphan from resolution_map's auto_merge.orphans by iso_code."""
    orphans = _resolution_map().auto_merge.orphans
    for bucket in (orphans.no_candidates, orphans.no_matches):
        if iso_code in bucket:
            bucket.remove(iso_code)
            _resolution_map().save(RESOLUTION_MAP_PATH)
            return
    for orphan in orphans.ambiguity:
        if orphan.iso_code == iso_code:
            orphans.ambiguity.remove(orphan)
            _resolution_map().save(RESOLUTION_MAP_PATH)
            return
    raise ValueError(f"{iso_code} is not in resolution_map's orphans")
