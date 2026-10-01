import re
from ingest.shared.models import SubdivisionModel

# only "city" is kept distinct; finer area distinctions (province/department/county/region/etc) aren't reliable across sources and fold into one "area" family instead
TYPE_FAMILIES = {
    "city": {"city", "shi", "si", "gorodskoy", "town", "linn"},
    "area": {
        "province",
        "vald",
        "provincia",
        "sheng",
        "district",
        "rayon",
        "raion",
        "okrug",
        "tumani",
        "járás",
        "okres",
        "amphoe",
        "huyện",
        "lçesi",
        "gu",
        "municipality",
        "comuna",
        "municipio",
        "kommun",
        "kommune",
        "gemeente",
        "obshtina",
        "commune",
        "region",
        "oblast",
        "kray",
        "kraj",
        "lan",
        "län",
        "state",
        "land",
        "department",
        "departamento",
        "county",
        "powiat",
        "shahrestān",
        "kabupaten",
        "gun",
        "governorate",
        "prefecture",
        "parish",
        "pagasts",
        "council",
        "republic",
        "respublika",
        "division",
        "canton",
        "voivodship",
    },
}

# prepositions/articles that carry no administrative meaning; noise for fuzzy matching but never a type qualifier
NON_TYPE_NOISE_TOKENS = {
    "of",
    "de",
    "du",
    "al",
    "the",
    "il",
    "is",
    "in",
    "ta",
    "ix",
    "iz",
    "iż",
    "di",
    "barrio",
}

NOISE_TOKENS = set.union(*TYPE_FAMILIES.values()) | NON_TYPE_NOISE_TOKENS

TOKEN_TO_FAMILY = {
    token: family for family, tokens in TYPE_FAMILIES.items() for token in tokens
}

# maps an ISO subdivision's own `type` field (lowercased) to "city" or "area"; types left unmapped are ambiguous/hybrid/rare and stay neutral
ISO_TYPE_FAMILIES = {
    "city": "city",
    "metropolitan city": "city",
    "city with county rights": "city",
    "state city": "city",
    "city municipality": "city",
    "town": "city",
    "province": "area",
    "district": "area",
    "municipality": "area",
    "region": "area",
    "state": "area",
    "department": "area",
    "county": "area",
    "governorate": "area",
    "prefecture": "area",
    "metropolitan department": "area",
    "parish": "area",
    "local council": "area",
    "rayon": "area",
    "administrative region": "area",
    "rural municipality": "area",
    "canton": "area",
    "metropolitan district": "area",
    "council area": "area",
    "urban municipality": "area",
    "two-tier county": "area",
    "republic": "area",
    "division": "area",
    "autonomous region": "area",
    "land": "area",
    "voivodship": "area",
    "special municipality": "area",
    "commune": "area",
    "metropolitan region": "area",
    "regional state": "area",
    "island council": "area",
    "oblast": "area",
    "autonomous district": "area",
    "free municipal consortium": "area",
    "district municipality": "area",
}


def strip_noise_tokens(s: str) -> str:
    """Remove common noise tokens from a subdivision name for better fuzzy matching."""
    tokens = re.split(r"\W+", s.lower())
    filtered = [t for t in tokens if t and t not in NOISE_TOKENS]
    return " ".join(filtered)


def raw_type_families(sub: SubdivisionModel) -> set[str]:
    """Return the set of type families whose qualifier tokens appear in sub's raw, unstripped name/aliases."""
    families = set()
    for text in [sub.name] + sub.aliases:
        for token in re.split(r"\W+", text.lower()):
            family = TOKEN_TO_FAMILY.get(token)
            if family:
                families.add(family)
    return families


def is_type_disqualified(iso_sub: SubdivisionModel, geo_sub: SubdivisionModel) -> bool:
    """True if geo_sub's raw qualifier words indicate a different administrative type than iso_sub's own ISO type (e.g. iso_sub is a City but geo_sub's raw aliases are all Oblast-qualified), and so should never be matched regardless of name similarity."""
    iso_family = ISO_TYPE_FAMILIES.get((iso_sub.type or "").lower())
    if iso_family is None:
        return False
    geo_families = raw_type_families(geo_sub)
    return bool(geo_families) and iso_family not in geo_families
