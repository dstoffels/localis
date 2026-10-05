import json
from ingest.shared.models import CurrencyModel
from ingest.utils import ingest_log
from .fetch_currencies import ISO_CURRENCIES_PATH


def load_currencies() -> dict[str, CurrencyModel]:
    """ISO 4217's currency and fund codes as published, keyed by alpha3."""
    ingest_log.writeline("Loading ISO 4217 currencies...")
    entries: list[dict[str, str]] = json.loads(ISO_CURRENCIES_PATH.read_text(encoding="utf-8"))["4217"]
    currencies: dict[str, CurrencyModel] = {}
    for entry in entries:
        alpha3, numeric = entry["alpha_3"], entry.get("numeric")
        if alpha3 in currencies:
            raise ValueError(f"iso-codes' iso_4217.json lists {alpha3} twice ({currencies[alpha3].name!r} and {entry['name']!r}), and a code must name one currency; check the file at the iso-codes commit in currencies.manifest.json and decide in load_currencies() which entry to keep")
        currencies[alpha3] = CurrencyModel(name=entry["name"], alpha3=alpha3, numeric=int(numeric) if numeric else None)
    return currencies
