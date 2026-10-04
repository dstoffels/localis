import re
from typing import Iterable
from localis.utils.strings import normalize

# abbreviations and spelling variants of the same word, folded together in name_key() only; shipped names keep their own spelling
_TOKEN_EQUIVALENTS = {
    "st": "saint",
    "ste": "sainte",
    "mt": "mount",
    "ft": "fort",
    "rep": "republic",
    "dem": "democratic",
    "sts": "states",
    "fed": "federal",
    "federated": "federal",
    **{form: "island" for form in ("i", "is", "isl", "isle", "isles", "islands")},
}
# words whose presence doesn't change which name it is: "Republic of Congo" / "Rep. Congo", "the Bahamas" / "Bahamas"
_FILLER_TOKENS = {"the", "of"}
_NON_WORD_RE = re.compile(r"[^\w\s]")


def name_key(name: str) -> str:
    """A comparison key under which spelling variants of one name are equal."""
    tokens = _NON_WORD_RE.sub(" ", normalize(name).replace("&", " and ")).split()
    return " ".join(_TOKEN_EQUIVALENTS.get(t, t) for t in tokens if t not in _FILLER_TOKENS)


def _fullness(s: str) -> tuple[int, int]:
    return len(s), sum(1 for ch in s if ord(ch) > 127)


def dedupe(items: Iterable[str], exclude: Iterable[str] = ()) -> list[str]:
    """Normalizes whitespace in each alias, drops empty ones and any variant of an `exclude` name, and keeps one per name_key(); sorted."""
    excluded = {name_key(e) for e in exclude if e}
    seen: dict[str, str] = {}
    for item in items:
        s = " ".join(item.split())
        key = name_key(s)
        if not key or key in excluded:
            continue
        # the fullest written form wins: longest ("Saint" over "St.", "Islands" over "Is."), then most accented ("Collectivité" over "Collectivite"), then alphabetical
        current = seen.get(key)
        if current is None or (_fullness(s), current) > (_fullness(current), s):
            seen[key] = s
    return sorted(seen.values())
