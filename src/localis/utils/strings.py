import unicodedata
import re
from functools import cache

SPACE_RE = re.compile(r"\s+")

# Latin letters NFKD doesn't decompose, keyed by casefolded form, and the modifier letters and punctuation found in the sources, folded to ASCII. Bespoke rather than unidecode, which is GPL-2.0-or-later and so can't be a dependency of this MIT package.
LATIN_FOLDS = str.maketrans(
    {
        "ı": "i",
        "ł": "l",
        "ø": "o",
        "đ": "d",
        "æ": "ae",
        "ð": "d",
        "œ": "oe",
        "ħ": "h",
        "þ": "th",
        "ə": "a",
        "ǝ": "a",
        "ɔ": "o",
        "ɛ": "e",
        "ɡ": "g",
        "ƣ": "oi",
        "ɕ": "c",
        "ƶ": "z",
        "ɣ": "g",
        "ɨ": "i",
        "ɵ": "o",
        "ɪ": "i",
        "ʊ": "u",
        "ɬ": "l",
        "ŋ": "ng",
        "ʂ": "s",
        "ʐ": "z",
        "ɲ": "n",
        "ɑ": "a",
        "ɾ": "r",
        "ʑ": "z",
        "ʒ": "z",
        "ƿ": "w",
        "ɩ": "i",
        "ʃ": "s",
        "ʁ": "r",
        "ȝ": "y",
        "ɞ": "e",
        "ɹ": "r",
        "ɐ": "a",
        "ꞑ": "n",
        "ʻ": "`",
        "ʾ": "`",
        "ʼ": "'",
        "ʿ": "'",
        "ˈ": "'",
        "ʹ": "'",
        "ˌ": ",",
        "ː": ":",
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "–": "-",
        "—": "--",
        "†": "+",
        # the regional indicator letters that spell flag emoji
        **{chr(cp): "" for cp in range(0x1F1E6, 0x1F200)},
    }
)
# \w counts the underscore as a word character, so it's matched separately
PUNCTUATION_RE = re.compile(r"[^\w\s]|_")
# the longest one-word name shipped for search's edit-distance fallback on short queries, one character past the longest query that uses it
SHORT_NAME_MAX = 7


@cache
def _is_latin(ch: str) -> bool:
    """Whether ch is a Latin base an accent can sit on: a Latin letter, or any ASCII character."""
    return ch.isascii() or unicodedata.name(ch, "").startswith("LATIN ")


def is_latin(s: str) -> bool:
    """Whether every letter in s is Latin script; modifier letters such as the ʻokina count as Latin."""
    return all(
        not ch.isalpha()
        or _is_latin(ch)
        or unicodedata.name(ch, "").startswith("MODIFIER LETTER ")
        for ch in s
    )


def normalize(s: str) -> str:
    """The casefolded comparison form of a string: Latin folded to ASCII, other scripts kept as written."""
    if s.isascii():
        return SPACE_RE.sub(" ", s.lower()).strip()

    kept: list[str] = []
    latin = False
    for ch in unicodedata.normalize("NFKD", s).casefold():
        if not unicodedata.combining(ch):
            latin = _is_latin(ch)
        # an accent on a Latin letter is dropped; marks on other scripts, such as Devanagari's nukta, are part of the letter
        elif latin:
            continue
        kept.append(ch)
    s = unicodedata.normalize("NFC", "".join(kept).translate(LATIN_FOLDS))
    return SPACE_RE.sub(" ", s).strip()


def search_text(s: str) -> str:
    """The form search compares on both the index and query side: normalize()'s form with punctuation turned into spaces."""
    return SPACE_RE.sub(" ", PUNCTUATION_RE.sub(" ", normalize(s))).strip()


def search_trigrams(s: str) -> set[str]:
    """The distinct trigrams of search_text(s), each word padded with two leading spaces and one trailing space so a short word keeps its edge trigrams through a typo."""
    trigrams: set[str] = set()
    for word in search_text(s).split():
        padded = f"  {word} "
        trigrams.update(padded[i : i + 3] for i in range(len(padded) - 2))
    return trigrams
