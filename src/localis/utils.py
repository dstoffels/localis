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


# The search indexes store tens of thousands of trigrams and some have thousands of associated IDs.
# To reduce the size of these indexes on disk, we encode the list of IDs for each trigram using
# base64-encoded delta encoding. Two formats are supported:
# - Legacy: varint delta encoding (slower, more compact)
# - Binary: array.array('I') delta encoding (10-50x faster, slightly larger)
def decode_id_list(b64: str) -> list[int]:
    """Convert base64(delta(ids)) → [1,5,6,...]. Supports both varint and array.array formats."""
    if not b64:
        return []
    
    data = base64.b64decode(b64)
    
    # Check for binary format marker (starts with 'BIN1' magic bytes)
    if data[:4] == b'BIN1':
        # Binary format: BIN1 header + array.array('I') delta-encoded values
        import array
        deltas = array.array('I')
        deltas.frombytes(data[4:])
        
        out = []
        prev = 0
        for delta in deltas:
            prev += delta
            out.append(prev)
        return out
    
    # Legacy varint format
    out = []
    prev = 0

    i = 0
    n = len(data)

    while i < n:
        shift = 0
        value = 0

        while True:
            b = data[i]
            i += 1
            value |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7

        prev += value
        out.append(prev)

    return out
