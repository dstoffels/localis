import json
from datetime import date
from ingest.shared.models import CountryModel, CurrencyModel
from ingest.utils import ingest_log
from .fetch_countries import CLDR_CURRENCY_DATA_PATH


def _legal_tender(country: CountryModel, entries: list[dict[str, dict[str, str]]], today: str) -> list[str]:
    """The codes of a territory's CLDR currency entries that are legal tender and in use today (started, and not ended before today), in CLDR's order; an entry dated to start or end later is logged, since CLDR announces changeovers ahead of them."""
    codes: list[str] = []
    for entry in entries:
        for code, info in entry.items():
            if info.get("_tender") == "false":
                continue
            starts, ends = info.get("_from", ""), info.get("_to")
            if starts > today:
                ingest_log.writeline(f"CLDR dates {country.alpha2} ({country.name}) currency {code} to start on {starts}; it ships from the first run on or after that date", level="WARN")
            if ends is not None and ends >= today:
                ingest_log.writeline(f"CLDR dates {country.alpha2} ({country.name}) currency {code} to end on {ends}; it stops shipping from the first run after that date", level="WARN")
            if starts <= today and (ends is None or ends >= today):
                codes.append(code)
    return codes


def place_currencies(countries: dict[str, CountryModel], currencies: dict[str, CurrencyModel]) -> None:
    """Sets each current country's legal-tender currencies from CLDR as of the run date; historic countries get none, since CLDR keys territories by alpha2 and ISO reused historic ones."""
    ingest_log.writeline("Placing countries' currencies...")
    regions: dict[str, list] = json.loads(CLDR_CURRENCY_DATA_PATH.read_text(encoding="utf-8"))["supplemental"]["currencyData"]["region"]
    # CLDR's dates are ISO 8601 days, so they compare as strings
    today = date.today().isoformat()

    without: list[str] = []
    for country in countries.values():
        if country.historic:
            continue
        for code in _legal_tender(country, regions.get(country.alpha2, []), today):
            currency = currencies.get(code)
            if currency is None:
                ingest_log.writeline(f"CLDR gives {country.alpha2} ({country.name}) currency {code}, which isn't in ISO 4217; skipped", level="WARN")
                continue
            country.currencies.append(currency)
        if not country.currencies:
            without.append(country.alpha2)

    linked = {c.alpha3 for country in countries.values() for c in country.currencies}
    ingest_log.writeline(f"{len(linked)} of {len(currencies)} currencies linked; current countries without one: {', '.join(without) or 'none'}")
