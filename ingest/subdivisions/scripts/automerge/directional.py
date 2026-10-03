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
