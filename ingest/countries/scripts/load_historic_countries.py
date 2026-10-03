# This script initializes historic (withdrawn) country entries from ISO 3166-3, keyed by
# alpha_4 since bare alpha2/alpha3 can be reused across two different historic entries
# (e.g. CS: Czechoslovakia CSHH, then later Serbia and Montenegro CSXX).

from ingest.utils import COUNTRIES_INPUTS_PATH, ingest_log
from ingest.shared.models import CountryModel
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
            comment = c.get("comment", "")

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
                historic=f"{alpha_4}|{c['withdrawal_date']}|{comment}",
            )

    return countries
