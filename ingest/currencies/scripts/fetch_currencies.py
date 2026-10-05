from ingest.utils import CURRENCIES, fetch

ISO_CURRENCIES_URL = "https://salsa.debian.org/iso-codes-team/iso-codes/-/raw/main/data/iso_4217.json"
ISO_CURRENCIES_PATH = CURRENCIES.inputs / "iso_4217.json"


def fetch_currencies_sources() -> None:
    """Downloads ISO 4217 if it changed."""
    fetch(ISO_CURRENCIES_URL, ISO_CURRENCIES_PATH, CURRENCIES.manifest)
