from data.subdivisions.utils import *
import re
from rapidfuzz import fuzz
from localis.models import SubdivisionModel
from localis.utils import normalize

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


def try_merge(iso_subs: dict[str, SubdivisionModel], sub_map: SubdivisionMap) -> None:

    unmatched_iso_subs: list[SubdivisionModel] = []

    print("Attemping to merge ISO to GeoNames subdivisions...")
    for _, iso_sub in iso_subs.items():
        iso_sub.aliases = dedupe(iso_sub.aliases)

        # Add the country if it wasn't added when caching GeoNames subdivisions (for safety) and add the ISO subdivision as is
        country_map = sub_map.filter(iso_sub.country.alpha2)
        if not country_map:
            print(f"Creating new country map for {iso_sub.country.name}")
            sub_map.add(iso_sub)
            continue

        # extract geonames subdivisions in map by country and admin level
        geo_subs = sub_map.filter(iso_sub.country.alpha2, iso_sub.admin_level)

        iso_names = prepare_names(iso_sub)

        # loop over each cached GeoNames subdivision and attempt to match with the ISO sub.
        for geo_sub in geo_subs:
            geo_names = prepare_names(geo_sub)

            if any(
                fuzz.token_set_ratio(iso_name, geo_name)
                >= threshold(iso_name, geo_name)
                and not has_directional_mismatch(iso_name, geo_name)
                for iso_name in iso_names
                for geo_name in geo_names
            ):
                merge_matched_sub(iso_sub, geo_sub)
                break
        else:
            unmatched_iso_subs.append(iso_sub)

    print(
        f"Merged {len(iso_subs) - len(unmatched_iso_subs)}/{len(iso_subs)} ISO subdivisions"
    )
    return unmatched_iso_subs
