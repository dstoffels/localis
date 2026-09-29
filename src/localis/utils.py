from array import array
import unicodedata
import re
from unidecode import unidecode
import base64

SPACE_RE = re.compile(r"\s+")


def normalize(s: str, lower: bool = True) -> str:
    """Custom transliteration of a string into an ASCII-only search form with optional lowercasing (default=True)."""
    if not isinstance(s, str):
        return s
    MAP = {"ə": "a", "ǝ": "ä"}

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = "".join(MAP.get(ch, ch) for ch in s)
    s = unidecode(s)
    s = SPACE_RE.sub(" ", s).strip()
    return s.lower() if lower else s


def generate_trigrams(s: str):
    if not s:
        return

    for i in range(max(len(s) - 2, 1)):
        yield s[i : i + 3]
