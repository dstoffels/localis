import json
from ingest.shared.models import CurrencyModel
from ingest.utils import ingest_log
from .fetch_currencies import ISO_CURRENCIES_PATH


def load_currencies() -> dict[str, CurrencyModel]:
    """ISO 4217's currency and fund codes as published, keyed by alpha3."""
    ingest_log.writeline("Loading ISO 4217 currencies...")
    entries: list[dict[str, str]] = json.loads(ISO_CURRENCIES_PATH.read_text(encoding="utf-8"))["4217"]
    currencies: dict[str, CurrencyModel] = {}
    for id, entry in enumerate(entries, start=1):
        numeric = entry.get("numeric")
        currencies[entry["alpha_3"]] = CurrencyModel(
            id=id, name=entry["name"], alpha3=entry["alpha_3"], numeric=int(numeric) if numeric else None
        )
    ingest_log.writeline(f"{len(currencies)} currencies")
    return currencies
