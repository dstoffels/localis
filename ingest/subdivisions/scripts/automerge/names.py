import re
from functools import cache
from localis.utils.strings import normalize
from ingest.shared.models import SubdivisionModel
from .type_families import strip_noise_tokens

_DROPPED_CHARS_RE = re.compile(r"[,\(\)\[\]\"']")


@cache
def _clean(s: str) -> str:
    """A name's fuzzy-matching form, cached per string since each name is scored against many others: normalized, hyphens and underscores as spaces, commas, brackets and quotes dropped, noise words stripped."""
    s = normalize(s).replace("-", " ").replace("_", " ")
    return strip_noise_tokens(_DROPPED_CHARS_RE.sub("", s).strip())


def prepare_names(sub: SubdivisionModel) -> list[str]:
    """The fuzzy-matching form of the sub's name and each alias."""
    return [_clean(sub.name), *map(_clean, sub.aliases)]
