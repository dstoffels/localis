import json
from ingest.shared.models import CountryModel, CurrencyModel
from ingest.utils import ingest_log
from .fetch_countries import CLDR_CURRENCY_DATA_PATH


def _legal_tender(entries: list[dict[str, dict[str, str]]]) -> list[str]:
    """The codes of a territory's CLDR currency entries still in use (no end date) and legal tender, in CLDR's order."""
    return [code for entry in entries for code, info in entry.items() if "_to" not in info and info.get("_tender") != "false"]


def place_currencies(countries: dict[str, CountryModel], currencies: dict[str, CurrencyModel]) -> None:
    """Sets each current country's legal-tender currencies from CLDR; historic countries get none, since CLDR keys territories by alpha2 and ISO reused historic ones."""
    ingest_log.writeline("Placing countries' currencies...")
    regions: dict[str, list] = json.loads(CLDR_CURRENCY_DATA_PATH.read_text(encoding="utf-8"))["supplemental"]["currencyData"]["region"]

    without: list[str] = []
    for country in countries.values():
        if country.historic:
            continue
        for code in _legal_tender(regions.get(country.alpha2, [])):
            currency = currencies.get(code)
            if currency is None:
                ingest_log.writeline(f"CLDR gives {country.alpha2} ({country.name}) currency {code}, which isn't in ISO 4217; skipped", level="WARN")
                continue
            country.currencies.append(currency)
        if not country.currencies:
            without.append(country.alpha2)

    linked = {c.alpha3 for country in countries.values() for c in country.currencies}
    ingest_log.writeline(f"{len(linked)} of {len(currencies)} currencies linked; current countries without one: {', '.join(without) or 'none'}")
