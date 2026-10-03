import functools
import json
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from typing import Literal
from ingest.subdivisions.utils.resolution_map import ResolutionMap, SkillDecision
from ingest.shared.models import SubdivisionModel
from ingest.utils import SUBDIVISIONS_OUTPUTS_PATH
from ingest.shared.scripts import load_countries
from ingest.subdivisions.scripts.automerge.type_families import is_type_disqualified, raw_type_families
from ingest.subdivisions.scripts import (
    load_iso_subs,
    map_geonames_subdivisions,
    merge_alternate_name_aliases,
    score_candidates,
)
from ingest.subdivisions.scripts.wikidata_subdivisions import CROSSWALK_PATH
from ingest.subdivisions.scripts.automerge.scoring import is_directional_mismatch

RESOLUTION_MAP_PATH = SUBDIVISIONS_OUTPUTS_PATH / "resolution_map.json"


@functools.cache
def _resolution_map() -> ResolutionMap:
    return ResolutionMap.load(RESOLUTION_MAP_PATH)


@functools.cache
def _crosswalk() -> dict[str, int]:
    """The Wikidata crosswalk the last ingest run fetched."""
    if not CROSSWALK_PATH.exists():
        return {}
    return json.loads(CROSSWALK_PATH.read_text(encoding="utf-8"))


def write_resolution(
    iso_code: str,
    geonames_id: int | None,
    reason: str | None,
    decided_by: Literal["agent", "human"],
    escalation: str | None,
) -> None:
    """geonames_id of None means "add as-is"."""
    resolution_map = _resolution_map()
    resolution_map.skill_decisions[iso_code] = SkillDecision(
        id=geonames_id,
        reason=reason,
        decided_by=decided_by,
        escalation=escalation,
        wikidata_seen=_crosswalk().get(iso_code),
    )
    resolution_map.save(RESOLUTION_MAP_PATH)


@functools.cache
def _countries():
    return load_countries()


def _apply_resolved_claims(sub_map: SubdivisionMap, resolution_map: ResolutionMap) -> None:
    """Marks every GeoNames sub already claimed by a recorded resolution, so a target another iso_code already has doesn't look unclaimed. A decision under review as a wikidata_conflict doesn't count as a claim, so keeping it stays possible."""
    under_review = {orphan.iso_code for orphan in resolution_map.automerge.orphans.wikidata_conflict}
    claims = {
        code: decision.id
        for code, decision in resolution_map.skill_decisions.items()
        if code not in under_review
    }
    for source in (claims, resolution_map.wikidata_merge, resolution_map.automerge.bypassed):
        for iso_code, geonames_id in source.items():
            if geonames_id is None:
                continue
            sub = sub_map.get(geonames_id=geonames_id)
            if sub is not None:
                sub.iso_code = iso_code
    for iso_code, match in resolution_map.automerge.resolutions.items():
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
    return iso_subs


def _format_candidate(candidate: SubdivisionModel, note: str = "") -> str:
    names = ", ".join([candidate.name, *candidate.aliases])
    label = f"{candidate.geonames_id}: {names} - [{candidate.admin_level}]"
    if candidate.iso_code is not None:
        label += f" CLAIMED BY {candidate.iso_code}"
    if note:
        label += f" ({note})"
    return label


TOP_TIER_MIN = 10
TOP_TIER_MAX = 100
TOP_TIER_FRACTION = 0.1
BATCH_SIZE = 200


def _get_top_tier_batch_size(pool_size: int) -> int:
    return min(max(TOP_TIER_MIN, round(pool_size * TOP_TIER_FRACTION)), TOP_TIER_MAX)


def _flagged_candidates(iso_code: str) -> list[tuple[int, str]]:
    """The specific records the pipeline flagged for this orphan, with a note saying why, shown as its first batch: ambiguity close-calls, the low_margin or grouping_twin pick, or both sides of a wikidata_conflict. Empty for no_candidates/no_matches; raises if iso_code isn't an orphan."""
    orphans = _resolution_map().automerge.orphans
    if iso_code in orphans.no_candidates or iso_code in orphans.no_matches:
        return []
    for orphan in orphans.ambiguity:
        if orphan.iso_code == iso_code:
            return [(gid, "automerge's contested target") for gid in orphan.candidate_geonames_ids]
    for orphan in orphans.low_margin:
        if orphan.iso_code == iso_code:
            return [(orphan.candidate_geonames_id, f"automerge's pick, {orphan.margin} points over threshold")]
    for orphan in orphans.grouping_twin:
        if orphan.iso_code == iso_code:
            return [(orphan.candidate_geonames_id, "automerge's pick, likely the record for this subdivision's non-administrative grouping")]
    for orphan in orphans.wikidata_conflict:
        if orphan.iso_code == iso_code:
            flagged = [(orphan.wikidata_geonames_id, "Wikidata's mapping")]
            if orphan.decision_geonames_id is not None:
                flagged.append((orphan.decision_geonames_id, "current skill decision"))
            return flagged
    raise ValueError(f"{iso_code} is not in resolution_map's orphans")


def get_candidates(iso_code: str, batch_num: int = 0) -> list[str]:
    """A batch of candidates, best first. A list rather than an id-keyed dict, since serialization sorts dict keys and would lose the ranking."""
    iso_sub: SubdivisionModel | None = _get_iso_subs().get(iso_code, None)
    if not iso_sub:
        raise ValueError(f"{iso_code} is not found in ISO subdivisions")

    flagged = _flagged_candidates(iso_code)
    flagged_ids = [gid for gid, _ in flagged]
    sub_map = get_geonames_submap()

    # ambiguity, low_margin and wikidata_conflict orphans see the specific records the pipeline flagged first, before the full pool
    if flagged and batch_num == 0:
        records = [(sub_map.get(geonames_id=gid), note) for gid, note in flagged]
        return [_format_candidate(c, note) for c, note in records if c is not None]

    # the whole country, claimed, type-mismatched and directional-mismatched records included (marked), since ISO and GeoNames can disagree on a subdivision's level or name the same place differently; on score ties, clean candidates come before mismatched ones and same-level before other levels
    same_level = min(iso_sub.admin_level, 2)
    geo_subs = [g for g in sub_map.filter(iso_sub.country.alpha2) if g.geonames_id not in flagged_ids]
    scored = score_candidates(iso_sub, geo_subs, include_type_disqualified=True, include_directional_mismatch=True)
    notes: dict[int | None, str] = {}
    for g, _, _ in scored:
        note = []
        if is_type_disqualified(iso_sub, g):
            note.append(_type_mismatch_note(iso_sub, g))
        if is_directional_mismatch(iso_sub, g):
            note.append("directional mismatch")
        if note:
            notes[g.geonames_id] = "; ".join(note)
    scored.sort(key=lambda t: (-t[1], t[0].geonames_id in notes, t[0].admin_level != same_level))
    candidates = [geo_sub for geo_sub, score, needed in scored]

    # a flagged first batch shifts normal pagination to start at batch 1
    effective_batch_num = batch_num - 1 if flagged_ids else batch_num
    top_tier_batch_size = _get_top_tier_batch_size(len(candidates))

    if effective_batch_num == 0:
        batch_start, batch_end = 0, top_tier_batch_size
    else:
        batch_start = top_tier_batch_size + (effective_batch_num - 1) * BATCH_SIZE
        batch_end = min(batch_start + BATCH_SIZE, len(candidates))

    if batch_start >= len(candidates):
        return []

    candidates = candidates[batch_start:batch_end]

    return [_format_candidate(c, notes.get(c.geonames_id, "")) for c in candidates]


def _type_mismatch_note(iso_sub: SubdivisionModel, candidate: SubdivisionModel) -> str:
    families = "/".join(sorted(raw_type_families(candidate)))
    return f"type mismatch: GeoNames name reads as {families}, ISO type is {iso_sub.type}"


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
    resolution_map = _resolution_map()
    orphans = resolution_map.automerge.orphans
    ambiguity_codes = [orphan.iso_code for orphan in orphans.ambiguity]
    low_margin_codes = [orphan.iso_code for orphan in orphans.low_margin]
    conflict_codes = [orphan.iso_code for orphan in orphans.wikidata_conflict]
    twin_codes = [orphan.iso_code for orphan in orphans.grouping_twin]
    iso_code = next(
        iter(orphans.no_candidates + orphans.no_matches + ambiguity_codes + low_margin_codes + conflict_codes + twin_codes),
        None,
    )
    if iso_code is None:
        return None

    iso_sub = _get_iso_subs()[iso_code]
    orphan = {
        "iso_code": iso_code,
        "name": iso_sub.name,
        "aliases": iso_sub.aliases,
        "country": iso_sub.country.name,
        "type": iso_sub.type,
        "admin_level": iso_sub.admin_level,
    }
    if iso_code in conflict_codes:
        decision = resolution_map.skill_decisions[iso_code]
        orphan["current_decision"] = {
            "geonames_id": decision.id if decision.id is not None else "add as-is (no GeoNames counterpart)",
            "reason": decision.reason,
        }
    return orphan


def pop_orphan(iso_code: str) -> None:
    """Removes an orphan from resolution_map's automerge.orphans by iso_code."""
    orphans = _resolution_map().automerge.orphans
    for bucket in (orphans.no_candidates, orphans.no_matches):
        if iso_code in bucket:
            bucket.remove(iso_code)
            _resolution_map().save(RESOLUTION_MAP_PATH)
            return
    for flagged_bucket in (orphans.ambiguity, orphans.low_margin, orphans.wikidata_conflict, orphans.grouping_twin):
        for orphan in flagged_bucket:
            if orphan.iso_code == iso_code:
                flagged_bucket.remove(orphan)
                _resolution_map().save(RESOLUTION_MAP_PATH)
                return
    raise ValueError(f"{iso_code} is not in resolution_map's orphans")
