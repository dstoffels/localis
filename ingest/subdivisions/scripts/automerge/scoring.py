from rapidfuzz import fuzz
from ingest.shared.models import SubdivisionModel
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from .directional import has_directional_mismatch
from .type_families import is_type_disqualified
from .names import prepare_names


def threshold(name_a: str, name_b: str) -> int:
    """Adjust the fuzzy matching threshold based on str length"""

    avg_len = (len(name_a) + len(name_b)) / 2

    threshold = 90

    # shorter names need looser thresholds
    if avg_len <= 5:
        threshold -= 15
    elif avg_len <= 8:
        threshold -= 10
    elif avg_len <= 12:
        threshold -= 5

    return threshold


def candidate_pool(
    sub_map: SubdivisionMap, alpha2: str, admin_level: int | None = None
) -> list[SubdivisionModel]:
    """Unclaimed GeoNames subdivisions for a country. admin_level=None returns every level; a concrete level restricts to it, capped at 2 since GeoNames never nests deeper."""
    if admin_level is None:
        return [g for g in sub_map.filter(alpha2) if g.iso_code is None]
    geonames_level = min(admin_level, 2)
    return [g for g in sub_map.filter(alpha2, geonames_level) if g.iso_code is None]


def score_candidates(
    iso_sub: SubdivisionModel,
    geo_subs: list[SubdivisionModel],
    include_type_disqualified: bool = False,
) -> list[tuple[SubdivisionModel, float, int]]:
    """Score every geo_sub candidate against iso_sub with the same rules auto-merge itself uses to decide a match: type-family disqualification, directional-mismatch exclusion, then the best-scoring name pair and its dynamic threshold. Returns (geo_sub, score, threshold_needed) for every non-disqualified candidate, best-first; include_type_disqualified keeps type-disqualified candidates too, for manual review where a type mismatch can be a naming difference rather than a different place. A caller filters `score >= threshold_needed` for "would qualify for auto-merge"; the full ranked list is also what should be shown for manual review, since a sub-threshold entry is a near-miss, not a refusal."""
    iso_names = prepare_names(iso_sub)
    scored: list[tuple[SubdivisionModel, float, int]] = []
    for geo_sub in geo_subs:
        if not include_type_disqualified and is_type_disqualified(iso_sub, geo_sub):
            continue
        best: tuple[float, int] | None = None
        for iso_name in iso_names:
            for geo_name in prepare_names(geo_sub):
                if has_directional_mismatch(iso_name, geo_name):
                    continue
                score = fuzz.token_sort_ratio(iso_name, geo_name)
                needed = threshold(iso_name, geo_name)
                if best is None or score > best[0]:
                    best = (score, needed)
        if best is not None:
            scored.append((geo_sub, best[0], best[1]))
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored
