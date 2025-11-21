def prep_fts_tokens(s: str, exact_match: bool) -> str:
    """Wrap each token in quotes and at * wildcard for prefixing if not exact_match"""
    if not s:
        return s

    tokens = s.split()
    for i, token in enumerate(tokens):
        tokens[i] = f'''"{token}"'''
        if not exact_match:
            tokens[i] += "*"
    final = " ".join(tokens)
    return final


def clean_row(row: dict[str, str]) -> dict[str, str | None]:
    """Clean and normalize all fields in a dict"""
    return {k: (v if v.strip() != "" else None) for k, v in row.items()}


def chunked(list: list, size: int):
    for i in range(0, len(list), size):
        yield list[i : i + size]


MAX_DIGITS = 8


def pad_num_w_zeros(val: str | int) -> str:
    """
    Pads a number with leading zeros to ensure a fixed width of 8 characters (up to 99,999,999).
    For consistent string-based sorting and comparison.
    """
    return f"{int(val):0{MAX_DIGITS}d}"
