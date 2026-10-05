import json
from collections import Counter
from pathlib import Path
from typing import Any
import localis
from localis.registries import Registry

ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / "src" / "localis" / "data"
RESOLUTION_MAP_PATH = (
    ROOT / "ingest" / "subdivisions" / "outputs" / "resolution_map.json"
)
CROSSWALK_PATH = ROOT / "ingest" / "subdivisions" / "inputs" / "wikidata_crosswalk.json"
CITIES_INGEST_STATS_PATH = ROOT / "ingest" / "cities" / "outputs" / "ingest_stats.json"
OUTPUT_PATH = Path(__file__).with_name("data_stats.json")
POPULATION_THRESHOLD = 15_000


def use_staging() -> None:
    """Points the stats at the pipeline's staged build instead of the shipped one: its data, read through localis's own registries, and the staged copies of the pipeline outputs it reads. The build must be complete, so a run stopped partway is never mixed with shipped data."""
    global DATA_PATH, CROSSWALK_PATH, CITIES_INGEST_STATS_PATH
    # imported here, so the unit tests that read these stats don't need the pipeline importable
    from ingest.utils import STAGED_DATA_PATH, is_complete, staged_path

    if not is_complete():
        raise RuntimeError("staging holds no complete build; run the pipeline")
    # set on analysis's side before any registry loads, so the runtime itself only ever reads its packaged data
    setattr(Registry, "_data_path", property(lambda self: STAGED_DATA_PATH / self.REGISTRY_NAME))
    DATA_PATH = STAGED_DATA_PATH
    CROSSWALK_PATH = CROSSWALK_PATH.with_suffix(".pending.json")
    CITIES_INGEST_STATS_PATH = staged_path(CITIES_INGEST_STATS_PATH)


def _country_stats() -> dict[str, int]:
    include_historic = localis.countries.include_historic
    localis.countries.set_include_historic(True)
    try:
        all_countries = list(localis.countries)
    finally:
        localis.countries.set_include_historic(include_historic)
    historic = [c for c in all_countries if c.historic]
    current = [c for c in all_countries if not c.historic]
    current_alpha2s = {c.alpha2 for c in current}
    return {
        "total": len(all_countries),
        "current": len(current),
        # every ISO 3166-1 country has a numeric code; Kosovo, added from GeoNames, has none
        "iso_current": sum(1 for c in current if c.numeric is not None),
        "historic": len(historic),
        "historic_reusing_current_alpha2": sum(
            1 for c in historic if c.alpha2 in current_alpha2s
        ),
    }


def _macroregion_stats() -> dict[str, int]:
    types = Counter(m.type for m in localis.macroregions)
    include_historic = localis.countries.include_historic
    localis.countries.set_include_historic(True)
    try:
        all_countries = list(localis.countries)
    finally:
        localis.countries.set_include_historic(include_historic)
    placed = [c for c in all_countries if c.macroregions]
    return {
        "total": len(localis.macroregions),
        "regions": types["region"],
        "subregions": types["subregion"],
        "groupings": types["grouping"],
        "current_placed": sum(1 for c in placed if not c.historic),
        "historic_placed": sum(1 for c in placed if c.historic),
    }


def _currency_stats() -> dict[str, int]:
    current = [c for c in localis.countries if not c.historic]
    linked = {c.id for country in current for c in country.currencies}
    return {
        "total": len(localis.currencies),
        "linked": len(linked),
        "current_countries_without": sum(1 for c in current if not c.currencies),
        "multi_currency_countries": sum(1 for c in current if len(c.currencies) > 1),
    }


def _script_stats() -> dict[str, int]:
    all_scripts = list(localis.scripts)
    return {
        "total": len(all_scripts),
        "with_aliases": sum(1 for s in all_scripts if s.aliases),
    }


def _language_stats() -> dict[str, int]:
    all_languages = list(localis.languages)
    current = [c for c in localis.countries if not c.historic]
    entries = [l for c in current for l in c.languages]
    return {
        "total": len(all_languages),
        "living": sum(1 for l in all_languages if l.type == "living"),
        "macrolanguages": sum(1 for l in all_languages if l.scope == "macrolanguage"),
        "with_alpha2": sum(1 for l in all_languages if l.alpha2),
        "with_scripts": sum(1 for l in all_languages if l.scripts),
        "with_aliases": sum(1 for l in all_languages if l.aliases),
        "country_entries": len(entries),
        "country_entries_with_script": sum(1 for l in entries if l.script),
        "current_countries_without": sum(1 for c in current if not c.languages),
    }


def _subdivision_stats() -> dict[str, Any]:
    subs = list(localis.subdivisions)
    iso_merged = sum(1 for s in subs if s.iso_code and s.geonames_id is not None)
    iso_only = sum(1 for s in subs if s.iso_code and s.geonames_id is None)
    geonames_only = sum(1 for s in subs if not s.iso_code)
    levels = Counter(s.admin_level for s in subs)
    return {
        "non_administrative": _non_administrative_stats(subs),
        "kosovo": _kosovo_stats(subs),
        "total": len(subs),
        "iso_total": iso_merged + iso_only,
        "iso_merged": iso_merged,
        "iso_merged_pct": round(100 * iso_merged / (iso_merged + iso_only), 1),
        "iso_only": iso_only,
        "geonames_total": iso_merged + geonames_only,
        "geonames_only": geonames_only,
        "by_level": {str(level): levels[level] for level in sorted(levels)},
    }


def _iso_children(subs: list) -> dict[int, list]:
    """Each subdivision's ISO children, by parent id."""
    children: dict[int, list] = {}
    for s in subs:
        if s.parent is not None and s.iso_code:
            children.setdefault(s.parent.id, []).append(s)
    return children


def _non_administrative_stats(subs: list) -> dict[str, Any]:
    """Per country, its non-administrative groupings and the ISO subdivisions they group."""
    children = _iso_children(subs)
    by_country: dict[str, dict[str, Any]] = {}
    for grouping in (s for s in subs if s.admin_level == 0):
        entry = by_country.setdefault(
            grouping.country.alpha2,
            {"groupings": 0, "children": 0, "children_by_type": Counter()},
        )
        entry["groupings"] += 1
        entry["children"] += len(children.get(grouping.id, []))
        entry["children_by_type"].update(
            child.type for child in children.get(grouping.id, [])
        )
    return {
        "countries": len(by_country),
        **{
            alpha2: {**e, "children_by_type": dict(e["children_by_type"])}
            for alpha2, e in sorted(by_country.items())
        },
    }


def _kosovo_stats(subs: list) -> dict[str, int]:
    """ISO's Serbian records for Kosovo and GeoNames' records under Kosovo, which ship side by side."""
    province = localis.subdivisions.lookup("RS-KM")
    assert (
        province is not None
    ), "RS-KM is missing, so methodology's Kosovo figures need rewriting"
    okrugs = len(_iso_children(subs).get(province.id, []))
    levels = Counter(s.admin_level for s in subs if s.country.alpha2 == "XK")
    return {
        "serbian_okrugs": okrugs,
        "serbian_records": okrugs + 1,
        "districts": levels[1],
        "municipalities": levels[2],
        "kosovan_records": sum(levels.values()),
    }


def _wikidata_stats() -> dict[str, int]:
    """The committed crosswalk against what shipped: a disagreement is an ISO code whose shipped GeoNames id isn't Wikidata's, and the populated-place pattern is a Wikidata target absent from the admin data."""
    crosswalk: dict[str, int] = json.loads(CROSSWALK_PATH.read_text(encoding="utf-8"))
    subs = list(localis.subdivisions)
    shipped = {s.iso_code: s.geonames_id for s in subs if s.iso_code}
    admin_ids = {s.geonames_id for s in subs if s.geonames_id is not None}
    disagreements = [
        code
        for code, geonames_id in crosswalk.items()
        if code in shipped and shipped[code] != geonames_id
    ]
    return {
        "crosswalk_codes": len(crosswalk),
        "disagreements": len(disagreements),
        "disagreements_not_admin": sum(
            1 for code in disagreements if crosswalk[code] not in admin_ids
        ),
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
    stats["total"] = sum(
        stats[k]
        for k in (
            "wikidata",
            "automerge",
            "skill_merge",
            "skill_add",
            "bypass_twinned",
            "bypass_untwinned",
            "geonames_absent",
        )
    )
    return stats


def _city_stats() -> dict[str, int]:
    threshold = localis.cities.population_threshold
    total = len(localis.cities)
    localis.cities.set_population_threshold(POPULATION_THRESHOLD)
    try:
        above = len(localis.cities)
    finally:
        localis.cities.set_population_threshold(threshold)
    ingest_stats = json.loads(CITIES_INGEST_STATS_PATH.read_text(encoding="utf-8"))
    return {
        "total": total,
        "threshold": POPULATION_THRESHOLD,
        "above_threshold": above,
        "ascii_names": ingest_stats["ascii_names"],
    }


def _filter_index_stats() -> dict[str, dict[str, int]]:
    """Per queryable registry, how many distinct filter values it indexes and how many belong to a single record."""
    stats: dict[str, dict[str, int]] = {}
    for offsets_path in sorted(DATA_PATH.glob("*/filter_index_offsets.tsv")):
        counts = [
            int(line.rsplit("\t", 1)[1])
            for line in offsets_path.read_text(encoding="utf-8").splitlines()
        ]
        stats[offsets_path.parent.name] = {
            "values": len(counts),
            "single_record_values": counts.count(1),
        }
    return stats


def _shipped_size_stats() -> dict[str, Any]:
    files_by_domain = {
        domain_path.name: {
            f.name: f.stat().st_size
            for f in sorted(domain_path.iterdir())
            if f.is_file()
        }
        for domain_path in sorted(p for p in DATA_PATH.iterdir() if p.is_dir())
    }
    totals = {domain: sum(files.values()) for domain, files in files_by_domain.items()}
    total = sum(totals.values())
    return {
        "total": total,
        **{
            domain: {
                "total": totals[domain],
                "share_pct": round(100 * totals[domain] / total, 1),
                "files": files,
            }
            for domain, files in files_by_domain.items()
        },
    }


def _reconcile(stats: dict[str, Any]) -> None:
    """Fails loudly if the counts don't add up, so a broken ingest can't publish inconsistent numbers."""
    subs, res, macro = stats["subdivisions"], stats["resolution"], stats["macroregions"]
    checks = {
        "macroregion types sum to the macroregions shipped": macro["total"]
        == macro["regions"] + macro["subregions"] + macro["groupings"],
        "every current country is placed in a macroregion": macro["current_placed"]
        == stats["countries"]["current"],
        "Kosovo's districts and municipalities are all its records": subs["kosovo"][
            "kosovan_records"
        ]
        == subs["kosovo"]["districts"] + subs["kosovo"]["municipalities"],
        "resolution sources sum to the ISO subdivisions shipped": res["total"]
        == subs["iso_total"],
        "merged ISO subdivisions match merging sources": subs["iso_merged"]
        == res["wikidata"]
        + res["automerge"]
        + res["skill_merge"]
        + res["bypass_twinned"],
        "ISO-only subdivisions match non-merging sources": subs["iso_only"]
        == res["skill_add"] + res["bypass_untwinned"] + res["geonames_absent"],
        "subdivision total is merged + ISO-only + GeoNames-only": subs["total"]
        == subs["iso_merged"] + subs["iso_only"] + subs["geonames_only"],
        "no orphans remain": res["orphans"] == 0,
        "skill decisions all have a decider": res["skill_by_agent"]
        + res["skill_by_human"]
        == res["skill_decisions"],
    }
    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise AssertionError("data stats don't reconcile: " + "; ".join(failed))


# the sections holding each registry's record count
REGISTRY_STATS = ("macroregions", "currencies", "scripts", "languages", "countries", "subdivisions", "cities")


def compute() -> dict[str, Any]:
    """Deterministic dataset statistics, reconciled against each other."""
    stats = {
        "macroregions": _macroregion_stats(),
        "countries": _country_stats(),
        "currencies": _currency_stats(),
        "scripts": _script_stats(),
        "languages": _language_stats(),
        "subdivisions": _subdivision_stats(),
        "resolution": _resolution_stats(),
        "wikidata": _wikidata_stats(),
        "cities": _city_stats(),
        "filter_index": _filter_index_stats(),
        "shipped_size": _shipped_size_stats(),
    }
    stats["totals"] = {"records": sum(stats[name]["total"] for name in REGISTRY_STATS)}
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
