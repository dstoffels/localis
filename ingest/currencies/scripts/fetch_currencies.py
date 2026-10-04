from ingest.utils import fetch
from ingest.utils import CURRENCIES_INPUTS_PATH, CURRENCIES_MANIFEST_PATH

ISO_CURRENCIES_URL = "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_4217.json"
ISO_CURRENCIES_PATH = CURRENCIES_INPUTS_PATH / "iso_4217.json"


def fetch_currencies_sources(force: bool = False) -> bool:
    """Downloads ISO 4217 if it changed; True if the stage should rebuild."""
    return fetch(ISO_CURRENCIES_URL, ISO_CURRENCIES_PATH, CURRENCIES_MANIFEST_PATH) or force
