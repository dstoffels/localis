import json
import sys
from pathlib import Path


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
PAGE_SIZE = 300


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


def get_all_country_candidates(iso_code: str) -> list[dict]:
    alpha2 = iso_code.split("-")[0]
    countries = load_countries()
    sub_map = map_geonames_subdivisions(countries)
    candidates = sorted(sub_map.filter(alpha2), key=lambda s: s.name)
    return [
        {
            "hashid": c.hashid,
            "name": c.name,
            "aliases": c.aliases,
            "admin_level": c.admin_level,
        }
        for c in candidates
    ]


def get_country_candidates_page(iso_code: str, page: int) -> list[dict]:
    all_candidates = get_all_country_candidates(iso_code)
    start = (page - 1) * PAGE_SIZE
    return all_candidates[start : start + PAGE_SIZE]


def log_decision(line: str) -> None:
    """Appends one human-readable line to resolution_log.txt, so every merge/add/skip
    decision (names, not just hashids) can be reviewed after the fact."""
    with open(RESOLUTION_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def pop_orphan(iso_code: str) -> None:
    """Removes iso_code from orphaned_subdivisions.json -- it's been resolved and recorded in resolution_map.json."""
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
