from ingest.utils import SUBDIVISIONS, CommittedQuery, ingest_log, sparql
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap, WikidataChangedOrphan, WikidataConflictOrphan
from ingest.shared.models import SubdivisionModel
from .automerge import merge_matched_sub

SPARQL_QUERY = """
SELECT ?isoCode ?geonamesId WHERE {
  ?item wdt:P300 ?isoCode .
  ?item wdt:P1566 ?geonamesId .
}
"""
# committed as the crosswalk's provenance; a removed mapping falls through to automerge unreviewed, so CommittedQuery confirms removals before keeping them
CROSSWALK = CommittedQuery[int](SUBDIVISIONS.inputs / "wikidata_crosswalk.json", "Wikidata crosswalk")


def _query_crosswalk() -> dict[str, int]:
    """Every (P300 ISO 3166-2 code, P1566 GeoNames id) pair on Wikidata, keeping only ISO codes with exactly one GeoNames id."""
    by_iso_code: dict[str, set[int]] = {}
    for binding in sparql(SPARQL_QUERY):
        iso_code = binding["isoCode"]["value"]
        geonames_id = int(binding["geonamesId"]["value"])
        by_iso_code.setdefault(iso_code, set()).add(geonames_id)
    return {code: next(iter(ids)) for code, ids in by_iso_code.items() if len(ids) == 1}


def fetch_wikidata_crosswalk() -> dict[str, int]:
    """Queries the crosswalk and stages it for promotion."""
    ingest_log.writeline("Querying Wikidata for ISO/GeoNames crosswalk...")
    return CROSSWALK.fetch(_query_crosswalk)


def _valid_target(crosswalk: dict[str, int], iso_code: str, sub_map: SubdivisionMap) -> SubdivisionModel | None:
    """The GeoNames subdivision Wikidata maps iso_code to, if it exists in localis's admin data and belongs to the same country."""
    geonames_id = crosswalk.get(iso_code)
    if geonames_id is None:
        return None
    mapped_sub = sub_map.get(geonames_id=geonames_id)
    if mapped_sub is None or mapped_sub.country.alpha2 != iso_code.split("-")[0]:
        return None
    return mapped_sub


def flag_wikidata_conflicts(
    crosswalk: dict[str, int],
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
    build_codes: set[str],
) -> None:
    """A skill decision may override Wikidata only knowingly: one that disagrees with a valid Wikidata mapping it wasn't made against (`wikidata_seen`) is sent back to the skill as a `wikidata_conflict` orphan. Recomputed every run, so a later change on Wikidata's side resurfaces the decision; an inactive decision, whose code isn't in this build, is left alone."""
    conflicts: list[WikidataConflictOrphan] = []
    for iso_code, decision in resolution_map.skill_decisions.items():
        if iso_code not in build_codes:
            continue
        mapped_sub = _valid_target(crosswalk, iso_code, sub_map)
        if mapped_sub is None:
            continue
        wikidata_id = mapped_sub.geonames_id
        assert wikidata_id is not None
        if wikidata_id == decision.id or wikidata_id == decision.wikidata_seen:
            continue
        ingest_log.writeline(
            f"wikidata conflict: skill decision {iso_code} -> {decision.id} disagrees with Wikidata's {mapped_sub.geonames_code} '{mapped_sub.name}' ({wikidata_id}), sent for review",
            level="WARN",
        )
        conflicts.append(
            WikidataConflictOrphan(iso_code=iso_code, wikidata_geonames_id=wikidata_id, decision_geonames_id=decision.id)
        )
    resolution_map.automerge.orphans.wikidata_conflict = conflicts


def _prior_targets(
    resolution_map: ResolutionMap, sub_map: SubdivisionMap, committed: dict[str, int]
) -> dict[str, int]:
    """What each iso_code resolved to before this run, read before it's recomputed: an unresolved wikidata_changed flag's previous target, else the committed crosswalk's valid mapping, else automerge's match."""
    prior = {code: match.id for code, match in resolution_map.automerge.resolutions.items()}
    for iso_code in committed:
        mapped_sub = _valid_target(committed, iso_code, sub_map)
        if mapped_sub is not None and mapped_sub.geonames_id is not None:
            prior[iso_code] = mapped_sub.geonames_id
    for orphan in resolution_map.automerge.orphans.wikidata_changed:
        prior[orphan.iso_code] = orphan.previous_geonames_id
    return prior


def apply_wikidata_matches(
    iso_subs: dict[str, SubdivisionModel],
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
    crosswalk: dict[str, int],
    committed: dict[str, int],
) -> dict[str, SubdivisionModel]:
    """Applies unambiguous Wikidata crosswalk matches for whatever skill_decisions didn't already claim, before auto-merge ever sees these iso_subs. A mapping that would change what an iso_code previously resolved to is held back as a wikidata_changed orphan instead; a code's first mapping applies as-is. Recomputed every run."""
    prior = _prior_targets(resolution_map, sub_map, committed)
    resolution_map.wikidata_merge = {}
    resolution_map.automerge.orphans.wikidata_changed = []
    remaining: dict[str, SubdivisionModel] = {}

    for iso_code, iso_sub in iso_subs.items():
        mapped_sub = _valid_target(crosswalk, iso_code, sub_map)
        if mapped_sub is None:
            remaining[iso_code] = iso_sub
            continue
        geonames_id = mapped_sub.geonames_id
        assert geonames_id is not None

        previous_id = prior.get(iso_code)
        if previous_id is not None and previous_id != geonames_id:
            ingest_log.writeline(
                f"wikidata changed: {iso_code} '{iso_sub.name}' now maps to {mapped_sub.geonames_code} '{mapped_sub.name}' ({geonames_id}), previously {previous_id}, sent for review",
                level="WARN",
            )
            resolution_map.automerge.orphans.wikidata_changed.append(
                WikidataChangedOrphan(iso_code=iso_code, previous_geonames_id=previous_id, wikidata_geonames_id=geonames_id)
            )
            continue

        if mapped_sub.iso_code and mapped_sub.iso_code != iso_code:
            ingest_log.writeline(
                f"wikidata conflict: {iso_code} '{iso_sub.name}'s target {mapped_sub.geonames_code} '{mapped_sub.name}' is already claimed by {mapped_sub.iso_code}",
                level="WARN",
            )
            remaining[iso_code] = iso_sub
            continue

        resolution_map.wikidata_merge[iso_code] = geonames_id
        merge_matched_sub(iso_sub, mapped_sub)

    ingest_log.writeline(
        f"resolved {len(resolution_map.wikidata_merge)}/{len(iso_subs)} subdivisions from Wikidata crosswalk, {len(resolution_map.automerge.orphans.wikidata_changed)} held back as changed"
    )
    return remaining
