from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.strings import dedupe
from ingest.subdivisions.utils.resolution_map import ResolutionMap, AutomergeMatch, AmbiguousOrphan, LowMarginOrphan
from ingest.shared.models import SubdivisionModel
from ingest.utils import ingest_log
from .scoring import candidate_pool, score_candidates
from .merge import merge_matched_sub

AMBIGUITY_THRESHOLD = 90
# a qualifying pair this close to its threshold is sent to the skill for review instead of merged
MARGIN_FLOOR = 5


def try_merge(
    iso_subs: dict[str, SubdivisionModel],
    sub_map: SubdivisionMap,
    resolution_map: ResolutionMap,
) -> None:
    """Auto-merges every iso_sub not already resolved by the resolve-subdivisions skill or bypassed as non-administrative. Writes every resolution and orphan directly into resolution_map.automerge, recomputed from scratch each run."""

    resolution_map.automerge.resolutions = {}
    resolution_map.automerge.orphans.no_candidates = []
    resolution_map.automerge.orphans.no_matches = []
    resolution_map.automerge.orphans.ambiguity = []
    resolution_map.automerge.orphans.low_margin = []
    resolution_map.automerge.geonames_absent = []

    unmerged_count = 0
    buckets: dict[tuple[str, int], list[SubdivisionModel]] = {}

    ingest_log.writeline("Attempting to merge ISO to GeoNames subdivisions...")
    for _, iso_sub in iso_subs.items():
        iso_sub.aliases = dedupe(iso_sub.aliases)

        # GeoNames has no subdivisions at all for this country (e.g. Singapore): nothing to merge with or review, so add as-is; recomputed every run, so it merges automatically if GeoNames ever adds records
        if not any(g.geonames_id is not None for g in sub_map.filter(iso_sub.country.alpha2)):
            assert iso_sub.iso_code is not None
            sub_map.add(iso_sub)
            resolution_map.automerge.geonames_absent.append(iso_sub.iso_code)
            unmerged_count += 1
            continue

        # GeoNames never nests beyond admin_level 2, so ISO subs at 2 and 3+ draw from the
        # same GeoNames pool (candidate_pool() caps the same way) and must compete together,
        # not in separate, order-dependent bucket passes.
        bucket_key = (iso_sub.country.alpha2, min(iso_sub.admin_level, 2))
        buckets.setdefault(bucket_key, []).append(iso_sub)

    # score every ISO/GeoNames pair within each country+admin_level bucket, then assign highest-scoring pairs first so a strong match can't be blocked by a weaker one claimed earlier merely because of iteration order.
    for (alpha2, admin_level), bucket_iso_subs in buckets.items():
        geo_subs = candidate_pool(sub_map, alpha2, admin_level)

        # snapshot each geo_sub's pre-merge name up front; merge_matched_sub() mutates geo_sub.name in place,
        # and a geo_sub can appear against several iso_subs in scored_pairs before one of them claims it.
        # geonames_id is always set here: candidate_pool() only returns unmerged GeoNames-sourced subs.
        geo_names_at_scoring: dict[int, str] = {}
        for g in geo_subs:
            assert g.geonames_id is not None
            geo_names_at_scoring[g.geonames_id] = g.name

        scored_pairs: list[tuple[float, int, SubdivisionModel, SubdivisionModel]] = []
        for iso_sub in bucket_iso_subs:
            for geo_sub, score, needed in score_candidates(iso_sub, geo_subs):
                if score >= needed:
                    scored_pairs.append((score, needed, iso_sub, geo_sub))

        scored_pairs.sort(key=lambda pair: pair[0], reverse=True)

        # a geo_sub that multiple distinct ISO subs both score >=95 against is a likely namesake
        # collision (e.g. a city and its own containing rayon sharing an identical name) that
        # string similarity can't safely break the tie on; exclude it entirely rather than let
        # the highest scorer quietly win what might be the wrong one.
        high_scorers: dict[int, set[str]] = {}
        for score, needed, iso_sub, geo_sub in scored_pairs:
            if score >= AMBIGUITY_THRESHOLD:
                assert geo_sub.geonames_id is not None
                assert iso_sub.iso_code is not None
                high_scorers.setdefault(geo_sub.geonames_id, set()).add(
                    iso_sub.iso_code
                )
        ambiguous_geo_ids = {
            geonames_id
            for geonames_id, iso_codes in high_scorers.items()
            if len(iso_codes) > 1
        }
        ambiguous_iso_codes: set[str] = set()
        for score, needed, iso_sub, geo_sub in scored_pairs:
            if geo_sub.geonames_id in ambiguous_geo_ids:
                assert iso_sub.iso_code is not None
                ambiguous_iso_codes.add(iso_sub.iso_code)
        # an iso_code can end up contesting more than one target (rare), so gather by iso_code
        # rather than writing one entry per target; orphans are ISO subs, so the orphan bucket
        # stays iso_code-primary like no_candidates/no_matches, just carrying multiple candidates.
        ambiguous_candidates: dict[str, list[int]] = {}
        for geonames_id in ambiguous_geo_ids:
            geo_name = geo_names_at_scoring[geonames_id]
            iso_codes = sorted(high_scorers[geonames_id])
            ingest_log.writeline(
                f"ambiguous target '{geo_name}': {', '.join(iso_codes)} all scored >= {AMBIGUITY_THRESHOLD}, excluding from auto-merge",
                level="WARN",
            )
            for iso_code in iso_codes:
                ambiguous_candidates.setdefault(iso_code, []).append(geonames_id)

        for iso_code, candidate_geonames_ids in ambiguous_candidates.items():
            resolution_map.automerge.orphans.ambiguity.append(
                AmbiguousOrphan(iso_code=iso_code, candidate_geonames_ids=candidate_geonames_ids)
            )

        claimed_iso: set[str] = set()
        claimed_geo: set[int] = set()
        low_margin_iso: set[str] = set()
        for score, needed, iso_sub, geo_sub in scored_pairs:
            assert geo_sub.geonames_id is not None
            assert iso_sub.iso_code is not None
            geo_name = geo_names_at_scoring[geo_sub.geonames_id]
            if iso_sub.iso_code in claimed_iso or iso_sub.iso_code in low_margin_iso:
                continue
            if geo_sub.geonames_id in ambiguous_geo_ids:
                continue
            if geo_sub.geonames_id in claimed_geo:
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' lost candidate {geo_sub.geonames_code} '{geo_name}' (score {score:.0f}) to a higher-scoring match",
                    level="WARN",
                )
                continue
            margin = round(score - needed)
            if margin < MARGIN_FLOOR:
                low_margin_iso.add(iso_sub.iso_code)
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' -> {geo_sub.geonames_code} '{geo_name}' ({score:.0f}/{needed}) below margin floor, sent for review",
                    level="WARN",
                )
                resolution_map.automerge.orphans.low_margin.append(
                    LowMarginOrphan(iso_code=iso_sub.iso_code, candidate_geonames_id=geo_sub.geonames_id, margin=margin)
                )
                continue
            merge_matched_sub(iso_sub, geo_sub)
            claimed_iso.add(iso_sub.iso_code)
            claimed_geo.add(geo_sub.geonames_id)
            resolution_map.automerge.resolutions[iso_sub.iso_code] = AutomergeMatch(id=geo_sub.geonames_id, margin=margin)
            if score < 90:
                ingest_log.writeline(
                    f"merged {iso_sub.iso_code} '{iso_sub.name}' -> {geo_sub.geonames_code} '{geo_name}' ({score:.0f}/{needed})"
                )

        bucket_unmerged = [
            iso_sub
            for iso_sub in bucket_iso_subs
            if iso_sub.iso_code not in claimed_iso
            and iso_sub.iso_code not in ambiguous_iso_codes
            and iso_sub.iso_code not in low_margin_iso
        ]
        for iso_sub in bucket_unmerged:
            candidates = score_candidates(iso_sub, geo_subs)
            candidate = candidates[0] if candidates else None
            if candidate is None:
                reason = "no_candidates"
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' unmerged: no GeoNames candidates in this bucket",
                    level="WARN",
                )
            else:
                reason = "no_matches"
                if candidate[1] < candidate[2]:
                    # only log a genuine near-miss (never qualified); a candidate that did
                    # qualify but lost the competition was already reported as "lost candidate" above
                    geo_sub, score, needed = candidate
                    assert geo_sub.geonames_id is not None
                    geo_name = geo_names_at_scoring[geo_sub.geonames_id]
                    ingest_log.writeline(
                        f"{iso_sub.iso_code} '{iso_sub.name}' unmerged: closest was {geo_sub.geonames_code} '{geo_name}' ({score:.0f}/{needed})",
                        level="WARN",
                    )
            assert iso_sub.iso_code is not None
            getattr(resolution_map.automerge.orphans, reason).append(iso_sub.iso_code)
        unmerged_count += len(bucket_iso_subs) - len(claimed_iso)

    ingest_log.writeline(
        f"Merged {len(iso_subs) - unmerged_count}/{len(iso_subs)} ISO subdivisions"
    )
    absent = resolution_map.automerge.geonames_absent
    if absent:
        ingest_log.writeline(f"{len(absent)} added as-is, their countries have no GeoNames subdivisions: {', '.join(absent)}")
    orphans = resolution_map.automerge.orphans
    ingest_log.writeline(f"{orphans.count()} subdivisions orphaned ({orphans.summary()})")
