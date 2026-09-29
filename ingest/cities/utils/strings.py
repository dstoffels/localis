import unicodedata


def normalize_name(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    return "".join(char for char in name.lower() if not unicodedata.combining(char))


ALLOWED_CHARS = set(" -'’")


def is_latin(name: str) -> bool:
    for c in name:
        if c.isalpha():
            try:
                if "LATIN" not in unicodedata.name(c):
                    return False
            except ValueError:
                return False
        elif c not in ALLOWED_CHARS:
            return False
    return True
