from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.strings import dedupe
from ingest.subdivisions.utils.resolution_map import ResolutionMap, AutoMergeMatch, AmbiguousOrphan
from ingest.shared.models import SubdivisionModel
from ingest.utils import ingest_log
from .scoring import candidate_pool, score_candidates
from .merge import merge_matched_sub

AMBIGUITY_THRESHOLD = 90


def try_merge(
    iso_subs: dict[str, SubdivisionModel],
    sub_map: SubdivisionMap,
    resolution_map: ResolutionMap,
) -> None:
    """Auto-merges every iso_sub not already resolved by the resolve-subdivisions skill or bypassed as non-administrative. Writes directly into resolution_map.auto_merge: a fresh result that matches what's already in `audited` is discarded (the audited entry is left as the authoritative record), otherwise it's written as a new, unaudited resolution/orphan, evicting any stale audited entry it contradicts."""

    resolution_map.auto_merge.resolutions = {}
    resolution_map.auto_merge.orphans.no_candidates = []
    resolution_map.auto_merge.orphans.no_matches = []
    resolution_map.auto_merge.orphans.ambiguity = []

    unmerged_count = 0
    buckets: dict[tuple[str, int], list[SubdivisionModel]] = {}

    ingest_log.writeline("Attempting to merge ISO to GeoNames subdivisions...")
    for _, iso_sub in iso_subs.items():
        iso_sub.aliases = dedupe(iso_sub.aliases)

        # Add the country if it wasn't added when caching GeoNames subdivisions (for safety) and add the ISO subdivision as is
        country_map = sub_map.filter(iso_sub.country.alpha2)
        if not country_map:
            ingest_log.writeline(f"Creating new country map for {iso_sub.country.name}")
            sub_map.add(iso_sub)
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
        geo_names_at_scoring: dict[int, str] = {g.geonames_id: g.name for g in geo_subs}

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
                high_scorers.setdefault(geo_sub.geonames_id, set()).add(
                    iso_sub.iso_code
                )
        ambiguous_geo_ids = {
            geonames_id
            for geonames_id, iso_codes in high_scorers.items()
            if len(iso_codes) > 1
        }
        ambiguous_iso_codes = {
            iso_sub.iso_code
            for score, needed, iso_sub, geo_sub in scored_pairs
            if geo_sub.geonames_id in ambiguous_geo_ids
        }
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
            if not resolution_map.reconcile(iso_code, None):
                resolution_map.auto_merge.orphans.ambiguity.append(
                    AmbiguousOrphan(iso_code=iso_code, candidate_geonames_ids=candidate_geonames_ids)
                )

        claimed_iso: set[str] = set()
        claimed_geo: set[int] = set()
        for score, needed, iso_sub, geo_sub in scored_pairs:
            geo_name = geo_names_at_scoring[geo_sub.geonames_id]
            if iso_sub.iso_code in claimed_iso:
                continue
            if geo_sub.geonames_id in ambiguous_geo_ids:
                continue
            if geo_sub.geonames_id in claimed_geo:
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' lost candidate {geo_sub.geonames_code} '{geo_name}' (score {score:.0f}) to a higher-scoring match",
                    level="WARN",
                )
                continue
            merge_matched_sub(iso_sub, geo_sub)
            claimed_iso.add(iso_sub.iso_code)
            claimed_geo.add(geo_sub.geonames_id)
            match = AutoMergeMatch(id=geo_sub.geonames_id, margin=round(score - needed))
            if not resolution_map.reconcile(iso_sub.iso_code, match.id):
                resolution_map.auto_merge.resolutions[iso_sub.iso_code] = match
            if score < 90:
                ingest_log.writeline(
                    f"merged {iso_sub.iso_code} '{iso_sub.name}' -> {geo_sub.geonames_code} '{geo_name}' ({score:.0f}/{needed})"
                )

        bucket_unmerged = [
            iso_sub
            for iso_sub in bucket_iso_subs
            if iso_sub.iso_code not in claimed_iso
            and iso_sub.iso_code not in ambiguous_iso_codes
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
                    geo_name = geo_names_at_scoring[geo_sub.geonames_id]
                    ingest_log.writeline(
                        f"{iso_sub.iso_code} '{iso_sub.name}' unmerged: closest was {geo_sub.geonames_code} '{geo_name}' ({score:.0f}/{needed})",
                        level="WARN",
                    )
            if not resolution_map.reconcile(iso_sub.iso_code, None):
                getattr(resolution_map.auto_merge.orphans, reason).append(
                    iso_sub.iso_code
                )
        unmerged_count += len(bucket_iso_subs) - len(claimed_iso)

    ingest_log.writeline(
        f"Merged {len(iso_subs) - unmerged_count}/{len(iso_subs)} ISO subdivisions"
    )
    orphans = resolution_map.auto_merge.orphans
    total_orphans = len(orphans.no_candidates) + len(orphans.no_matches) + len(orphans.ambiguity)
    ingest_log.writeline(
        f"{total_orphans} subdivisions orphaned "
        f"(no_candidates={len(orphans.no_candidates)}, no_matches={len(orphans.no_matches)}, ambiguity={len(orphans.ambiguity)})"
    )
