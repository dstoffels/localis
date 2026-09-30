from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.strings import dedupe
import re
from rapidfuzz import fuzz
from ingest.shared.models import SubdivisionModel
from localis.utils.strings import normalize
from ingest.utils import ingest_log

DIRECTIONAL_TOKENS = {
    "north",
    "south",
    "east",
    "west",
    "northern",
    "southern",
    "eastern",
    "western",
    "upper",
    "lower",
    "central",
}


def has_directional_mismatch(name1: str, name2: str) -> bool:
    """Check if two names have mismatched directional tokens to prevent merging between directional divisions of the same name (i.e. East Germany and West Germany should not merge)."""
    tokens1 = set(name1.lower().split())
    tokens2 = set(name2.lower().split())
    return any(t in tokens1 ^ tokens2 for t in DIRECTIONAL_TOKENS)


CATEGORICAL_TOKENS = {
    "okrug",
    "oblast",
    "kray",
    "kraj",
    "lan",
    "län",
    "rayon",
    "comuna",
    "district",
    "province",
    "region",
    "state",
    "shi",
    "sheng",
    "county",
    "parish",
    "barrio",
    "lçesi",
    "gun",
    "pagasts",
    "municipality",
    "kommun",
    "tumani",
    "járás",
    "department",
    "raion",
    "si",
    "kommune",
    "city",
    "gu",
    "division",
    "municipio",
    "provincia",
    "di",
    "kabupaten",
    "departamento",
    "shahrestān",
    "powiat",
    "gemeente",
    "obshtina",
    "okres",
    "amphoe",
    "huyện",
    "gorodskoy",
    "of",
    "de",
    "du",
    "council",
    "al",
    "the",
    "il",
    "is",
    "in",
    "ta",
    "ix",
    "iz",
    "iż",
    "republic",
    "respublika",
}


def strip_cat_tokens(s: str) -> str:
    """Remove common categorical tokens from a subdivision name for better fuzzy matching."""
    tokens = re.split(r"\W+", s.lower())
    filtered = [t for t in tokens if t and t not in CATEGORICAL_TOKENS]
    return " ".join(filtered)


def prepare_names(sub: SubdivisionModel) -> list[str]:
    """Combine and normalize all names for comparison"""

    def clean(s: str) -> str:
        s = normalize(s)
        s = s.replace("-", " ").replace("_", " ")
        s = re.sub(r"[,\(\)\[\]\"']", "", s).strip()
        return strip_cat_tokens(s)

    return [clean(sub.name)] + [clean(n) for n in sub.aliases]


def merge_matched_sub(iso_sub: SubdivisionModel, geo_sub: SubdivisionModel) -> None:
    """Merge ISO subdivision data into the corresponding GeoNames subdivision."""
    geo_sub.type = iso_sub.type
    geo_sub.iso_code = iso_sub.iso_code
    geo_sub.admin_level = iso_sub.admin_level
    current_name = geo_sub.name
    if geo_sub.name != iso_sub.name and geo_sub.name not in geo_sub.aliases:
        geo_sub.aliases.append(current_name)
        geo_sub.name = iso_sub.name
    geo_sub.aliases.extend(iso_sub.aliases)
    geo_sub.aliases = dedupe(geo_sub.aliases)

    dupes = []
    for alt in geo_sub.aliases:
        if alt == geo_sub.name:
            dupes.append(alt)

    for d in dupes:
        geo_sub.aliases.remove(d)


def threshold(name_a: str, name_b: str) -> int:
    """Adjust the fuzzy matching threshold based on token count and str length"""

    tokens_a, tokens_b = name_a.split(), name_b.split()
    token_count = max(len(tokens_a), len(tokens_b))
    avg_len = (len(name_a) + len(name_b)) / 2

    threshold = 90

    # shorter names need looser thresholds
    if avg_len <= 5:
        threshold -= 15
    elif avg_len <= 8:
        threshold -= 10
    elif avg_len <= 12:
        threshold -= 5

    # single token names
    if token_count == 1:
        threshold -= 5

    # hard min limit of 70
    return threshold


def best_match_score(iso_names: list[str], geo_names: list[str]) -> float | None:
    """Return the highest score among name pairs clearing their own dynamic threshold, or None if no pair qualifies."""
    best: float | None = None
    for iso_name in iso_names:
        for geo_name in geo_names:
            if has_directional_mismatch(iso_name, geo_name):
                continue
            score = fuzz.token_sort_ratio(iso_name, geo_name)
            if score >= threshold(iso_name, geo_name) and (
                best is None or score > best
            ):
                best = score
    return best


def best_raw_candidate(
    iso_sub: SubdivisionModel, geo_subs: list[SubdivisionModel]
) -> tuple[SubdivisionModel, float, int] | None:
    """Diagnostic only: find the single highest-scoring geo_sub for iso_sub, ignoring the qualifying threshold, so a true orphan's closest miss is visible. Returns (geo_sub, score, threshold_needed) or None if geo_subs is empty."""
    iso_names = prepare_names(iso_sub)
    best: tuple[SubdivisionModel, float, int] | None = None
    for geo_sub in geo_subs:
        for iso_name in iso_names:
            for geo_name in prepare_names(geo_sub):
                if has_directional_mismatch(iso_name, geo_name):
                    continue
                score = fuzz.token_sort_ratio(iso_name, geo_name)
                if best is None or score > best[1]:
                    best = (geo_sub, score, threshold(iso_name, geo_name))
    return best


def try_merge(
    iso_subs: dict[str, SubdivisionModel], sub_map: SubdivisionMap
) -> list[SubdivisionModel]:

    unmerged_iso_subs: list[SubdivisionModel] = []
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

        bucket_key = (iso_sub.country.alpha2, iso_sub.admin_level)
        buckets.setdefault(bucket_key, []).append(iso_sub)

    # score every ISO/GeoNames pair within each country+admin_level bucket, then assign highest-scoring pairs first so a strong match can't be blocked by a weaker one claimed earlier merely because of iteration order.
    for (alpha2, admin_level), bucket_iso_subs in buckets.items():
        geo_subs = [
            g for g in sub_map.filter(alpha2, admin_level) if g.iso_code is None
        ]

        # snapshot each geo_sub's pre-merge name up front; merge_matched_sub() mutates geo_sub.name in place,
        # and a geo_sub can appear against several iso_subs in scored_pairs before one of them claims it.
        geo_names_at_scoring: dict[int, str] = {g.hashid: g.name for g in geo_subs}

        scored_pairs: list[tuple[float, SubdivisionModel, SubdivisionModel]] = []
        for iso_sub in bucket_iso_subs:
            iso_names = prepare_names(iso_sub)
            for geo_sub in geo_subs:
                score = best_match_score(iso_names, prepare_names(geo_sub))
                if score is not None:
                    scored_pairs.append((score, iso_sub, geo_sub))

        scored_pairs.sort(key=lambda pair: pair[0], reverse=True)

        # a geo_sub that multiple distinct ISO subs both score >=95 against is a likely namesake
        # collision (e.g. a city and its own containing rayon sharing an identical name) that
        # string similarity can't safely break the tie on; exclude it entirely rather than let
        # the highest scorer quietly win what might be the wrong one.
        AMBIGUITY_THRESHOLD = 90
        high_scorers: dict[int, set[str]] = {}
        for score, iso_sub, geo_sub in scored_pairs:
            if score >= AMBIGUITY_THRESHOLD:
                high_scorers.setdefault(geo_sub.hashid, set()).add(iso_sub.iso_code)
        ambiguous_geo_ids = {
            hashid for hashid, iso_codes in high_scorers.items() if len(iso_codes) > 1
        }
        for hashid in ambiguous_geo_ids:
            geo_name = geo_names_at_scoring[hashid]
            iso_codes = ", ".join(sorted(high_scorers[hashid]))
            ingest_log.writeline(
                f"ambiguous target '{geo_name}': {iso_codes} all scored >= {AMBIGUITY_THRESHOLD}, excluding from auto-merge",
                level="WARN",
            )

        claimed_iso: set[str] = set()
        claimed_geo: set[int] = set()
        for score, iso_sub, geo_sub in scored_pairs:
            geo_name = geo_names_at_scoring[geo_sub.hashid]
            if iso_sub.iso_code in claimed_iso:
                continue
            if geo_sub.hashid in ambiguous_geo_ids:
                continue
            if geo_sub.hashid in claimed_geo:
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' lost candidate {geo_sub.geonames_code} '{geo_name}' (score {score:.0f}) to a higher-scoring match",
                    level="WARN",
                )
                continue
            merge_matched_sub(iso_sub, geo_sub)
            claimed_iso.add(iso_sub.iso_code)
            claimed_geo.add(geo_sub.hashid)
            if score < 90:
                ingest_log.writeline(
                    f"merged {iso_sub.iso_code} '{iso_sub.name}' -> {geo_sub.geonames_code} '{geo_name}' (score {score:.0f})"
                )

        bucket_unmerged = [
            iso_sub
            for iso_sub in bucket_iso_subs
            if iso_sub.iso_code not in claimed_iso
        ]
        for iso_sub in bucket_unmerged:
            candidate = best_raw_candidate(iso_sub, geo_subs)
            if candidate is None:
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' unmerged: no GeoNames candidates in this bucket",
                    level="WARN",
                )
            elif candidate[1] < candidate[2]:
                # only log a genuine near-miss (never qualified); a candidate that did
                # qualify but lost the competition was already reported as "lost candidate" above
                geo_sub, score, needed = candidate
                geo_name = geo_names_at_scoring[geo_sub.hashid]
                ingest_log.writeline(
                    f"{iso_sub.iso_code} '{iso_sub.name}' unmerged: closest was {geo_sub.geonames_code} '{geo_name}' ({score:.0f}/{needed})",
                    level="WARN",
                )
        unmerged_iso_subs.extend(bucket_unmerged)

    ingest_log.writeline(
        f"Merged {len(iso_subs) - len(unmerged_iso_subs)}/{len(iso_subs)} ISO subdivisions"
    )
    return unmerged_iso_subs
