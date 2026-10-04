# This script builds ISO 4217's currency and fund codes as published by iso-codes; which ones each country uses comes from CLDR in the countries stage.

from .fetch_currencies import fetch_currencies_sources
from .load_currencies import load_currencies
from ingest.shared.models import CurrencyModel
from ingest.utils import ingest_log, commit_manifest, dump_registry, CURRENCIES_MANIFEST_PATH


def ingest_currencies(force: bool = False) -> dict[str, CurrencyModel] | None:
    ingest_log.set_stage("CURRENCIES")
    try:
        has_update = fetch_currencies_sources(force=force)
        if not has_update:
            ingest_log.writeline("No updates for currencies.")
            return None
        currencies = load_currencies()
        dump_registry("currencies", list(currencies.values()))
        commit_manifest(CURRENCIES_MANIFEST_PATH)
        ingest_log.writeline(f"completed: {len(currencies)} currencies")
        return currencies
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_currencies(force=True)
