# Loads ISO 3166-3's withdrawn countries, keyed by alpha_4 since ISO reuses alpha2/alpha3 (CS: Czechoslovakia CSHH, then Serbia and Montenegro CSXX).

from ingest.utils import COUNTRIES_INPUTS_PATH, ingest_log
from ingest.shared.models import CountryModel, HistoricModel
import json


def init_historic_countries(
    countries: dict[str, CountryModel],
) -> dict[str, CountryModel]:
    """Parses country data from ISO 3166-3 and returns an alpha_4 mapped cache"""
    ingest_log.writeline("Loading historic ISO countries...")

    with open(COUNTRIES_INPUTS_PATH / "iso_3166-3.json", "r", encoding="utf-8") as f:
        historic_countries: list[dict] = json.load(f).get("3166-3")
        historic_countries.sort(key=lambda c: c.get("alpha_4") or "")

        for c in historic_countries:
            alpha_4 = c["alpha_4"]
            numeric = c.get("numeric")

            countries[alpha_4] = CountryModel(
                id=len(countries) + 1,
                name=c["name"],
                official_name=c.get("official_name"),
                common_name=None,
                alpha2=c["alpha_2"],
                alpha3=c["alpha_3"],
                geonames_id=None,
                numeric=int(numeric) if numeric else None,
                aliases=[],
                flag=None,
                historic=HistoricModel(alpha_4=alpha_4, withdrawal_date=c["withdrawal_date"], comment=c.get("comment") or None),
            )

    return countries


def historic_by_alpha2(countries: dict[str, CountryModel]) -> dict[str, list[CountryModel]]:
    """Historic entries grouped by their former alpha-2, each group ordered by withdrawal date, so a reused code's most recent holder is last."""
    grouped: dict[str, list[CountryModel]] = {}
    historic = [(c, c.historic) for c in countries.values() if c.historic]
    for c, _ in sorted(historic, key=lambda pair: pair[1].withdrawal_date):
        grouped.setdefault(c.alpha2, []).append(c)
    return grouped
