import json
from collections import Counter
from pathlib import Path
from typing import Any
import localis

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "src" / "localis" / "data"
RESOLUTION_MAP_PATH = ROOT / "ingest" / "subdivisions" / "outputs" / "resolution_map.json"
OUTPUT_PATH = Path(__file__).with_name("data_stats.json")
POPULATION_THRESHOLD = 15_000


def _country_stats() -> dict[str, int]:
    include_historic = localis.countries.include_historic
    localis.countries.set_include_historic(True)
    try:
        all_countries = list(localis.countries)
    finally:
        localis.countries.set_include_historic(include_historic)
    historic = sum(1 for c in all_countries if c.historic)
    return {"total": len(all_countries), "current": len(all_countries) - historic, "historic": historic}


def _subdivision_stats() -> dict[str, Any]:
    subs = list(localis.subdivisions)
    iso_merged = sum(1 for s in subs if s.iso_code and s.geonames_id is not None)
    iso_only = sum(1 for s in subs if s.iso_code and s.geonames_id is None)
    geonames_only = sum(1 for s in subs if not s.iso_code)
    levels = Counter(s.admin_level for s in subs)
    return {
        "total": len(subs),
        "iso_total": iso_merged + iso_only,
        "iso_merged": iso_merged,
        "iso_merged_pct": round(100 * iso_merged / (iso_merged + iso_only), 1),
        "iso_only": iso_only,
        "geonames_total": iso_merged + geonames_only,
        "geonames_only": geonames_only,
        "by_level": {str(level): levels[level] for level in sorted(levels)},
    }


def _resolution_stats() -> dict[str, int]:
    resolution_map = json.loads(RESOLUTION_MAP_PATH.read_text(encoding="utf-8"))
    automerge = resolution_map["automerge"]
    decisions = resolution_map["skill_decisions"].values()
    bypassed = automerge["bypassed"].values()
    stats = {
        "wikidata": len(resolution_map["wikidata_merge"]),
        "automerge": len(automerge["resolutions"]),
        "skill_merge": sum(1 for d in decisions if d["id"] is not None),
        "skill_add": sum(1 for d in decisions if d["id"] is None),
        "bypass_twinned": sum(1 for geonames_id in bypassed if geonames_id is not None),
        "bypass_untwinned": sum(1 for geonames_id in bypassed if geonames_id is None),
        "geonames_absent": len(automerge["geonames_absent"]),
        "skill_by_agent": sum(1 for d in decisions if d["decided_by"] == "agent"),
        "skill_by_human": sum(1 for d in decisions if d["decided_by"] == "human"),
        "orphans": sum(len(bucket) for bucket in automerge["orphans"].values()),
    }
    stats["skill_decisions"] = stats["skill_merge"] + stats["skill_add"]
    stats["total"] = sum(stats[k] for k in ("wikidata", "automerge", "skill_merge", "skill_add", "bypass_twinned", "bypass_untwinned", "geonames_absent"))
    return stats


def _city_stats() -> dict[str, int]:
    threshold = localis.cities.population_threshold
    total = len(localis.cities)
    localis.cities.set_population_threshold(POPULATION_THRESHOLD)
    try:
        above = len(localis.cities)
    finally:
        localis.cities.set_population_threshold(threshold)
    return {"total": total, "threshold": POPULATION_THRESHOLD, "above_threshold": above}


def _shipped_size_stats() -> dict[str, Any]:
    files_by_domain = {
        domain_path.name: {f.name: f.stat().st_size for f in sorted(domain_path.iterdir()) if f.is_file()}
        for domain_path in sorted(p for p in DATA_PATH.iterdir() if p.is_dir())
    }
    totals = {domain: sum(files.values()) for domain, files in files_by_domain.items()}
    total = sum(totals.values())
    return {
        "total": total,
        **{
            domain: {"total": totals[domain], "share_pct": round(100 * totals[domain] / total, 1), "files": files}
            for domain, files in files_by_domain.items()
        },
    }


def _reconcile(stats: dict[str, Any]) -> None:
    """Fails loudly if the counts don't add up, so a broken ingest can't publish inconsistent numbers."""
    subs, res = stats["subdivisions"], stats["resolution"]
    checks = {
        "resolution sources sum to the ISO subdivisions shipped": res["total"] == subs["iso_total"],
        "merged ISO subdivisions match merging sources": subs["iso_merged"] == res["wikidata"] + res["automerge"] + res["skill_merge"] + res["bypass_twinned"],
        "ISO-only subdivisions match non-merging sources": subs["iso_only"] == res["skill_add"] + res["bypass_untwinned"] + res["geonames_absent"],
        "subdivision total is merged + ISO-only + GeoNames-only": subs["total"] == subs["iso_merged"] + subs["iso_only"] + subs["geonames_only"],
        "no orphans remain": res["orphans"] == 0,
        "skill decisions all have a decider": res["skill_by_agent"] + res["skill_by_human"] == res["skill_decisions"],
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise AssertionError("data stats don't reconcile: " + "; ".join(failed))


def compute() -> dict[str, Any]:
    """Deterministic dataset statistics, reconciled against each other."""
    stats = {
        "countries": _country_stats(),
        "subdivisions": _subdivision_stats(),
        "resolution": _resolution_stats(),
        "cities": _city_stats(),
        "shipped_size": _shipped_size_stats(),
    }
    _reconcile(stats)
    return stats


def run() -> dict[str, Any]:
    """Computes the stats and overwrites data_stats.json."""
    stats = compute()
    OUTPUT_PATH.write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats


def main() -> None:
    print(json.dumps(run(), indent=2))


if __name__ == "__main__":
    main()
