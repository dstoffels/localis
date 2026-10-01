import functools
import json
import sys
from pathlib import Path
from rapidfuzz import fuzz
from ingest.subdivisions.scripts import prepare_names, load_iso_subs, merge_ipregistry_aliases
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.shared.models import SubdivisionModel


def _find_project_root(start: Path) -> Path:
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError(
        f"Could not locate project root (no pyproject.toml above {start})"
    )


sys.path.insert(0, str(_find_project_root(Path(__file__).resolve())))

from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH
from ingest.shared.scripts import load_countries
from ingest.subdivisions.scripts import map_geonames_subdivisions

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


@functools.cache
def get_geonames_submap() -> SubdivisionMap:
    return map_geonames_subdivisions(_countries())


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


def _rank_candidates(
    iso_sub: SubdivisionModel, candidates: list[SubdivisionModel]
) -> list[SubdivisionModel]:
    """Orders candidates by their best name/alias match against any of the ISO names"""
    iso_names = prepare_names(iso_sub)

    def score_candidate(candidate: SubdivisionModel) -> float:
        return max(
            fuzz.WRatio(i, n) for i in iso_names for n in prepare_names(candidate)
        )

    return sorted(candidates, key=score_candidate, reverse=True)


TOP_TIER_MIN = 10
TOP_TIER_MAX = 100
TOP_TIER_FRACTION = 0.1
BATCH_SIZE = 200


def _get_top_tier_batch_size(pool_size: int) -> int:
    return min(max(TOP_TIER_MIN, round(pool_size * TOP_TIER_FRACTION)), TOP_TIER_MAX)


def get_candidates(
    iso_code: str, batch_num: int = 0, return_all: bool = False
) -> dict[int, str]:
    # Look up iso_sub
    iso_sub: SubdivisionModel | None = _get_iso_subs().get(iso_code, None)
    if not iso_sub:
        raise ValueError(f"{iso_code} is not found in ISO subdivisions")

    # Map subdivisions, excluding candidates already claimed by another ISO subdivision
    sub_map = get_geonames_submap()
    geo_subs = [c for c in sub_map.filter(iso_sub.country.alpha2) if c.iso_code is None]

    candidates = _rank_candidates(iso_sub, geo_subs)

    if not return_all:
        top_tier_batch_size = _get_top_tier_batch_size(len(candidates))

        if batch_num == 0:
            batch_start, batch_end = 0, top_tier_batch_size
        else:
            batch_start = top_tier_batch_size + (batch_num - 1) * BATCH_SIZE
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
    iso_code = next(
        iter(orphans.no_candidates + orphans.no_matches + orphans.ambiguity), None
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
    for bucket in (orphans.no_candidates, orphans.no_matches, orphans.ambiguity):
        if iso_code in bucket:
            bucket.remove(iso_code)
            _resolution_map().save(RESOLUTION_MAP_PATH)
            return
    raise ValueError(f"{iso_code} is not in resolution_map's orphans")
