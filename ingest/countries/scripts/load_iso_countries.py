# Loads ISO 3166-1's countries, whose names ship as published; GeoNames and Wikidata add aliases later.

from ingest.utils import COUNTRIES, ingest_log
from ingest.shared.models import CountryModel
import json


def load_iso_countries() -> dict[str, CountryModel]:
    """ISO 3166-1's countries as published, keyed by alpha2."""
    ingest_log.writeline("Loading ISO countries...")
    countries: dict[str, CountryModel] = {}

    with open(COUNTRIES.inputs / "iso_3166-1.json", "r", encoding="utf-8") as f:
        iso_countries: list[dict] = json.load(f).get("3166-1")
        iso_countries.sort(key=lambda c: c.get("alpha_2") or "")

        for c in iso_countries:
            alpha2 = c["alpha_2"]
            countries[alpha2] = CountryModel(
                name=c["name"],
                official_name=c.get("official_name"),
                common_name=c.get("common_name"),
                alpha2=alpha2,
                alpha3=c["alpha_3"],
                geonames_id=None,
                numeric=int(c["numeric"]),
                aliases=[],
                flag=c["flag"],
                historic=None,
            )

    return countries
