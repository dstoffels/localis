import unicodedata, re
from unidecode import unidecode


def normalize(s: str, lower=True) -> str:
    """Lowers, strips most punctuation, and normalizes unicode. Keeps apostrophes."""
    if not isinstance(s, str):
        return s

    if lower:
        s = s.lower()

    s = unidecode(s)
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def tokenize(*parts: str) -> str:
    seen = set()
    tokens = []
    for part in parts:
        for token in normalize(part).split():
            if token not in seen:
                seen.add(token)
                tokens.append(token)
    return " ".join(tokens)


def extract_iso_code(address: dict) -> str | None:
    for key, value in address.items():
        if re.match(r"ISO3166-2-lvl\d+$", key):
            return value.replace(".", "-")
    return None


def normalize_name(name: str) -> str:
    if not name:
        return ""

    disallowed_pattern = re.compile(r"[^a-zA-Z0-9\u00C0-\u00FF\u0100-\u017F\s\'\-]")

    if disallowed_pattern.search(name):
        return ""

    return name.strip()


def parse_other_names(name, other_names: dict[str, str]) -> tuple[str, str]:
    name = normalize_name(name)

    if not other_names:
        return name, ""

    en_name = normalize_name(other_names.pop("name:en", None))
    names = set(other_names.values())
    normalized_names = {normalize(n) for n in names if n}
    other_names_str = " ".join(normalized_names)

    if en_name:
        return en_name, other_names_str
    return name, other_names_str


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
