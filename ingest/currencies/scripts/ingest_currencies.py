# This stage builds ISO 4217's currency and fund codes as published by iso-codes; which ones each country uses comes from CLDR in the countries stage.

from .fetch_currencies import fetch_currencies_sources
from .load_currencies import load_currencies
from ingest.shared.models import CurrencyModel
from ingest.utils import CURRENCIES, ingest_log, dump_registry


def ingest_currencies() -> dict[str, CurrencyModel]:
    with ingest_log.stage(CURRENCIES):
        fetch_currencies_sources()
        currencies = load_currencies()
        dump_registry("currencies", list(currencies.values()))
        ingest_log.writeline(f"completed: {len(currencies)} currencies")
        return currencies
