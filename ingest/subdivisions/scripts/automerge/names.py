import re
from localis.utils.strings import normalize
from ingest.shared.models import SubdivisionModel
from .type_families import strip_noise_tokens


def prepare_names(sub: SubdivisionModel) -> list[str]:
    """Combine and normalize all names for comparison"""

    def clean(s: str) -> str:
        s = normalize(s)
        s = s.replace("-", " ").replace("_", " ")
        s = re.sub(r"[,\(\)\[\]\"']", "", s).strip()
        return strip_noise_tokens(s)

    return [clean(sub.name)] + [clean(n) for n in sub.aliases]
