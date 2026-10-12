from typing import Literal
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ContestedDecisionOrphan, NewCandidateOrphan, ResolutionMap, RetiredDecision, StaleDecisionOrphan
from ingest.utils import ingest_log
from .automerge import merge_matched_sub, qualifying_candidates
from ingest.shared.models import SubdivisionModel


def retire_decisions(resolution_map: ResolutionMap, build_codes: set[str], bypassed_codes: set[str]) -> None:
    """Moves to retired_decisions every skill decision whose code ISO no longer lists or the pipeline now bypasses as non-administrative; one-way, so a code that returns is reviewed again rather than silently given its old decision."""
    for iso_code in sorted(resolution_map.skill_decisions):
        because: Literal["removed_from_iso", "bypassed"]
        if iso_code in bypassed_codes:
            because = "bypassed"
        elif iso_code not in build_codes:
            because = "removed_from_iso"
        else:
            continue
        decision = resolution_map.skill_decisions.pop(iso_code)
        resolution_map.retired_decisions[iso_code] = RetiredDecision(decision=decision, retired_because=because)
        ingest_log.writeline(f"retired skill decision {iso_code} -> {decision.id} ({because})", level="WARN")


def apply_skill_decisions(
    iso_subs: dict[str, SubdivisionModel],
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
) -> dict[str, SubdivisionModel]:
    """Applies every skill decision before Wikidata or automerge sees these iso_subs, so neither can replace one. A merge whose target GeoNames deleted (stale) or another decision also names (contested) goes back to the skill instead, and isn't returned as remaining, so nothing else takes it unreviewed. Returns the iso_subs with no decision."""
    orphans = resolution_map.automerge.orphans
    orphans.stale_decision = []
    orphans.contested_decision = []

    decisions = {code: decision for code, decision in resolution_map.skill_decisions.items() if code in iso_subs}
    # every merge decision by its target, so two naming one record are both caught, whichever comes first
    codes_by_target: dict[int, list[str]] = {}
    for iso_code, decision in decisions.items():
        if decision.id is not None:
            codes_by_target.setdefault(decision.id, []).append(iso_code)

    remaining: dict[str, SubdivisionModel] = {}
    applied = 0
    for iso_code, iso_sub in iso_subs.items():
        decision = decisions.get(iso_code)
        if decision is None:
            remaining[iso_code] = iso_sub
            continue
        if decision.id is None:
            sub_map.add(iso_sub)
            applied += 1
            continue

        target = sub_map.get(geonames_id=decision.id)
        claimants = set(codes_by_target[decision.id])
        # a target claimed outside the skill decisions is contested too, though nothing claims one before they apply
        if target is not None and target.iso_code is not None:
            claimants.add(target.iso_code)
        contested_with = sorted(claimants - {iso_code})
        if contested_with:
            ingest_log.writeline(f"contested skill decision: {iso_code} '{iso_sub.name}' -> {decision.id} is also named by {', '.join(contested_with)}, sent for review", level="WARN")
            orphans.contested_decision.append(ContestedDecisionOrphan(iso_code=iso_code, decision_geonames_id=decision.id, contested_with=contested_with))
            continue
        if target is None:
            ingest_log.writeline(f"stale skill decision: {iso_code} '{iso_sub.name}' -> {decision.id}, no longer in GeoNames, sent for review", level="WARN")
            orphans.stale_decision.append(StaleDecisionOrphan(iso_code=iso_code, decision_geonames_id=decision.id))
            continue

        merge_matched_sub(iso_sub, target)
        applied += 1

    ingest_log.writeline(f"resolved {applied}/{len(iso_subs)} subdivisions from skill decisions, {len(orphans.stale_decision)} stale, {len(orphans.contested_decision)} contested")
    return remaining


def flag_new_candidates(
    iso_subs: dict[str, SubdivisionModel],
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
) -> None:
    """Sends an add decision back to the skill when GeoNames now has a qualifying record for it that wasn't among its candidates_seen; run once every recomputed source has claimed what it will, so only genuinely unclaimed records count. A decision with no candidates_seen yet records its current ones as its baseline instead, since every add was made with its full candidate list in view."""
    orphans = resolution_map.automerge.orphans
    orphans.new_candidate = []
    # an add already sent back, such as a wikidata_conflict, sits in one bucket only
    already_orphaned = set(orphans.codes())
    baselined = 0
    for iso_code, decision in resolution_map.skill_decisions.items():
        if decision.id is not None or iso_code not in iso_subs or iso_code in already_orphaned:
            continue
        iso_sub = iso_subs[iso_code]
        qualifying = qualifying_candidates(iso_sub, sub_map)
        if decision.candidates_seen is None:
            decision.candidates_seen = qualifying
            baselined += 1
            continue
        new = [geonames_id for geonames_id in qualifying if geonames_id not in decision.candidates_seen]
        if new:
            ingest_log.writeline(f"new candidate for add decision {iso_code} '{iso_sub.name}': GeoNames {', '.join(map(str, new))} qualifies since it was decided, sent for review", level="WARN")
            orphans.new_candidate.append(NewCandidateOrphan(iso_code=iso_code, candidate_geonames_ids=new))
    if baselined:
        ingest_log.writeline(f"recorded candidates_seen for {baselined} add decisions that had none")
