# Loads ISO 3166-1's countries, whose names ship as published; GeoNames and Wikidata add aliases later.

from ingest.utils import COUNTRIES_INPUTS_PATH, ingest_log
from ingest.shared.models import CountryModel
import json


def init_iso_countries() -> dict[str, CountryModel]:
    """Parses country data from ISO 3166-1 and returns an alpha2 mapped cache"""
    ingest_log.writeline("Loading ISO countries...")
    countries: dict[str, CountryModel] = {}

    with open(COUNTRIES_INPUTS_PATH / "iso_3166-1.json", "r", encoding="utf-8") as f:
        iso_countries: list[dict] = json.load(f).get("3166-1")
        iso_countries.sort(key=lambda c: c.get("alpha_2") or "")

        for id, c in enumerate(iso_countries, 1):
            alpha2 = c["alpha_2"]
            countries[alpha2] = CountryModel(
                id=id,
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
