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


def get_orphan(iso_code: str) -> dict:
    orphaned = read_orphaned()
    if iso_code not in orphaned:
        raise ValueError(f"{iso_code} is not in orphaned_subdivisions.json")
    return orphaned[iso_code]


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
    return (
        candidate.hashid,
        f'{candidate.name} {" ".join(candidate.aliases)} [{candidate.admin_level}]',
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


TIER_ONE_MIN = 10
TIER_ONE_MAX = 100
TIER_ONE_FRACTION = 0.1


def _get_tier_size(pool_size: int) -> int:
    return min(max(TIER_ONE_MIN, round(pool_size * TIER_ONE_FRACTION)), TIER_ONE_MAX)


def get_candidates(iso_code: str, return_all: bool = False) -> dict[int, str]:
    # Look up iso_sub
    iso_sub: SubdivisionModel | None = _get_iso_subs().get(iso_code, None)
    if not iso_sub:
        raise ValueError(f"{iso_code} is not found in ISO subdivisions")

    # Map subdivisions
    sub_map = get_geonames_submap()
    geo_subs = sub_map.filter(iso_sub.country.alpha2)

    candidates = _rank_candidates(iso_sub, geo_subs)
    cutoff = _get_tier_size(len(candidates))
    candidates = candidates[cutoff:] if return_all else candidates[:cutoff]

    return dict(_format_candidate(c) for c in candidates if c.iso_code is None)


def is_valid_candidate(iso_code: str, geo_sub_hashid: int) -> bool:
    """True if geo_sub_hashid actually belongs to iso_code's own country's candidate pool."""
    iso_sub = _get_iso_subs().get(iso_code)
    if not iso_sub:
        return False
    sub_map = get_geonames_submap()
    return any(
        c.hashid == geo_sub_hashid for c in sub_map.filter(iso_sub.country.alpha2)
    )


def get_next_orphan(return_all: bool = False) -> dict:
    orphaned = read_orphaned()
    if not orphaned:
        return None

    iso_code, entry = next(iter(orphaned.items()))
    result = {"iso_code": iso_code, **entry}
    result["candidates"] = get_candidates(iso_code, return_all=return_all)
    return result


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


def mark_skipped(iso_code: str, reason: str) -> None:
    """Annotates iso_code in place as escalated to a human, without removing it from the queue."""
    orphaned = read_orphaned()
    if iso_code not in orphaned:
        raise ValueError(f"{iso_code} is not in orphaned_subdivisions.json")
    orphaned[iso_code]["skipped"] = True
    orphaned[iso_code]["reason"] = reason
    ORPHANED_PATH.write_text(
        json.dumps(orphaned, indent=2, ensure_ascii=False), encoding="utf-8"
    )
