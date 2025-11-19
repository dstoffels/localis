def prep_tokens(query: str, exact_match: bool) -> str:
    """Wrap each token in quotes and at * wildcard for prefixing if not exact_match"""

    tokens = query.split()
    for i, token in enumerate(tokens):
        tokens[i] = f'"{token}"'
        if not exact_match:
            tokens[i] += "*"
    return " ".join(tokens)


def clean_row(row: dict[str, str]) -> dict[str, str | None]:
    """Clean and normalize all fields in a dict"""
    return {k: (v if v.strip() != "" else None) for k, v in row.items()}


def chunked(list: list, size: int):
    for i in range(0, len(list), size):
        yield list[i : i + size]
