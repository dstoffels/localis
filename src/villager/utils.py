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
