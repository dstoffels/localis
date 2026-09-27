import functools
import json
import sys
from pathlib import Path
from rapidfuzz import process, fuzz
from data.subdivisions.scripts.merge_subdivisions import prepare_names
from data.subdivisions.scripts.iso_subdivisions import load_iso_subs
from data.subdivisions.subdivisions_utils import SubdivisionMap
from localis.models.subdivision import SubdivisionModel


def _find_project_root(start: Path) -> Path:
    for parent in (start, *start.parents):
        if (parent / "pyproject.toml").exists():
            return parent
    raise RuntimeError(
        f"Could not locate project root (no pyproject.toml above {start})"
    )


sys.path.insert(0, str(_find_project_root(Path(__file__).resolve())))

from data.utils import SUBDIVISIONS_RAW_PATH, load_countries
from data.subdivisions.scripts.geonames_subdivisions import map_geonames_subdivisions

RESOLUTION_MAP_PATH = SUBDIVISIONS_RAW_PATH / "resolution_map.json"
ORPHANED_PATH = SUBDIVISIONS_RAW_PATH / "orphaned_subdivisions.json"
RESOLUTION_LOG_PATH = SUBDIVISIONS_RAW_PATH / "resolution_log.txt"
REVIEW_OUTPUT_PATH = SUBDIVISIONS_RAW_PATH / "review_output.json"


def _read_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def read_resolution() -> dict:
    return _read_json(RESOLUTION_MAP_PATH) or {}


def read_orphaned() -> dict[str, dict]:
    """Keyed by iso_code, matching the shape resolve_subdivisions.py's handle_orphans() writes."""
    return _read_json(ORPHANED_PATH) or {}


def write_resolution(iso_code: str, entry: dict) -> None:
    resolution_map = _read_json(RESOLUTION_MAP_PATH) or {}
    resolution_map[iso_code] = entry
    RESOLUTION_MAP_PATH.write_text(
        json.dumps(resolution_map, indent=2, ensure_ascii=False), encoding="utf-8"
    )


@functools.cache
def _countries():
    return load_countries()


@functools.cache
def get_geonames_submap() -> SubdivisionMap:
    return map_geonames_subdivisions(_countries())


@functools.cache
def _get_iso_subs() -> dict[str, SubdivisionModel]:
    return load_iso_subs(_countries())


def _format_candidate(candidate: SubdivisionModel) -> tuple[int, str]:
    names = ", ".join([candidate.name, *candidate.aliases])
    return (
        candidate.hashid,
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
            return None

        candidates = candidates[batch_start:batch_end]

    return dict(_format_candidate(c) for c in candidates) or None


def is_valid_candidate(iso_code: str, geo_sub_hashid: int) -> tuple[bool, str]:
    """(True, "") if geo_sub_hashid belongs to iso_code's own country's candidate pool and hasn't already been claimed by another orphan; otherwise (False, <error message>)."""

    iso_sub = _get_iso_subs().get(iso_code)
    if iso_sub is None:
        return False, "ERROR: Invalid candidate: ISO subdivision not found"

    candidate = get_geonames_submap().get(geo_sub_hashid)
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


def get_next_orphan() -> dict:
    orphans = read_orphaned()
    if not orphans:
        return None

    iso_code, entry = next(iter(orphans.items()))
    return {"iso_code": iso_code, **entry}


def write_orphan_for_review(orphan: dict) -> None:
    """Writes the given orphan to the review output."""
    with open(REVIEW_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(orphan, f, indent=2, ensure_ascii=False)


def log_decision(line: str) -> None:
    with open(RESOLUTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pop_orphan(iso_code: str) -> None:
    """Removes an orphan from orphaned_subdivisions.json by iso_code"""
    orphaned = read_orphaned()
    if iso_code not in orphaned:
        raise ValueError(f"{iso_code} is not in orphaned_subdivisions.json")
    del orphaned[iso_code]
    ORPHANED_PATH.write_text(
        json.dumps(orphaned, indent=2, ensure_ascii=False), encoding="utf-8"
    )
