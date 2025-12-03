import unicodedata
import re
from unidecode import unidecode

ModelData = list[str | int | list[str] | None]
"""Raw model data list"""


def clean_row(row: dict[str, str]) -> dict[str, str | None]:
    """Clean and normalize all fields in a dict"""
    return {k: (v if v.strip() != "" else None) for k, v in row.items()}


def chunked(list: list, size: int):
    for i in range(0, len(list), size):
        yield list[i : i + size]


def normalize(s: str, lower: bool = True) -> str:
    """Custom transliteration of a string into an ASCII-only search form with optional lowercasing (default=True)."""
    if not isinstance(s, str):
        return s
    MAP = {"ə": "a", "ǝ": "ä"}

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = "".join(MAP.get(ch, ch) for ch in s)
    s = unidecode(s).strip()
    return s.lower() if lower else s


re_non_alphanumeric = re.compile(r"[^a-z0-9\s]+")
re_whitespace = re.compile(r"\s+")


def generate_trigrams(s: str):
    if not s:
        return

    for i in range(max(len(s) - 2, 1)):
        yield s[i : i + 3]


def generate_tokens(s: str):
    if not s:
        return

    s = s.replace(",", "").replace(".", "")
    for token in s.split():
        yield token


def generate_token_trigrams(s: str):
    norm = normalize(s)
    for token in generate_tokens(norm):
        yield from generate_trigrams(token)
