from ingest.utils import CURRENCIES, fetch, iso_codes_url

ISO_CURRENCIES_PATH = CURRENCIES.inputs / "iso_4217.json"


def fetch_currencies_sources() -> None:
    """Downloads ISO 4217 if it changed."""
    fetch(iso_codes_url(ISO_CURRENCIES_PATH.name), ISO_CURRENCIES_PATH, CURRENCIES.manifest)
