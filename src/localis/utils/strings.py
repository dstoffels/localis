import unicodedata
import re
from unidecode import unidecode

SPACE_RE = re.compile(r"\s+")
PUNCTUATION_RE = re.compile(r"[^\w\s]")
# the longest one-word name shipped for search's edit-distance fallback on short queries, one character past the longest query that uses it
SHORT_NAME_MAX = 7


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


def search_text(s: str) -> str:
    """The form search compares on both the index and query side: normalize()'s ASCII form with punctuation turned into spaces."""
    return SPACE_RE.sub(" ", PUNCTUATION_RE.sub(" ", normalize(s))).strip()


def search_trigrams(s: str) -> set[str]:
    """The distinct trigrams of search_text(s), each word padded with two leading spaces and one trailing space so a short word keeps its edge trigrams through a typo."""
    trigrams: set[str] = set()
    for word in search_text(s).split():
        padded = f"  {word} "
        trigrams.update(padded[i : i + 3] for i in range(len(padded) - 2))
    return trigrams
