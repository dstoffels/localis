# This script initializes the dataset from ISO 3166-1, with a few contemporary naming updates and aliases.
# These will be merged with data from their GeoNames and Wikipedia counterparts.

from data.utils import *
from localis.models import CountryModel
import json


def init_iso_countries() -> dict[str, CountryModel]:
    """Parses country data from ISO 3166-1 and returns an alpha2 mapped cache"""
    countries: dict[str, CountryModel] = {}

    # contemporary name mappings
    NAME_MAP = {
        "CG": "Republic of the Congo",
        "CD": "Democratic Republic of the Congo",
        "FK": "Falkland Islands",
        "FM": "Micronesia",
        "MF": "Saint-Martin",
        "SX": "Sint Maarten",
        "PS": "Palestine",
        "SH": "Saint Helena",
        "VA": "Holy See",
        "VG": "British Virgin Islands",
        "VI": "U.S. Virgin Islands",
        "VN": "Viet Nam",
    }

    OFFICIAL_NAME_MAP = {
        "FK": "Falkland Islands (Malvinas)",
        "KR": "Republic of Korea",
        "LA": "Lao People's Democratic Republic",
        "MF": "Collectivity of Saint Martin",
        "SX": "Country of Sint Maarten",
        "SH": "Saint Helena, Ascension and Tristan da Cunha",
        "SY": "Syrian Arab Republic",
        "TW": "Republic of China",
        "VA": "Vatican City State",
    }

    ALIAS_MAP = {
        "GB": [
            "Great Britain",
            "Britain",
            "UK",
            "England",
            "Scotland",
            "Wales",
            "Northern Ireland",
        ],
        "US": ["America"],
        "CI": ["Ivory Coast", "Cote d'Ivoire"],
        "MM": ["Burma"],
        "SZ": ["Swaziland"],
        "NL": ["Holland"],
        "MK": ["Macedonia"],
        "CV": ["Cape Verde"],
        "SY": ["Syria"],
        "RU": ["Russia", "USSR", "Soviet Union"],
        "VN": ["Vietnam"],
        "CG": ["Congo-Brazzaville", "Congo Republic"],
        "CD": ["DRC", "Congo-Kinshasa", "DR Congo", "Zaire"],
        "BN": ["Brunei"],
        "ST": ["São Tomé and Príncipe"],
        "TL": ["East Timor"],
        "RS": ["Yugoslavia"],
        "BQ": ["Netherlands Antilles", "Dutch Antilles", "Carribean Netherlands"],
        "SX": ["Land Sint Maarten", "Dutch Sint Maarten"],
        "MF": ["Collectivité de Saint-Martin"],
        "TW": ["ROC"],
    }

    with open(COUNTRIES_SRC_PATH / "iso3166-1.json", "r", encoding="utf-8") as f:
        iso_countries: list[dict] = json.load(f).get("3166-1")
        iso_countries.sort(key=lambda c: c.get("alpha_2"))

        for id, c in enumerate(iso_countries, 1):
            alpha2 = c["alpha_2"]
            # Prioritize name by mapping > common name field > name field
            name = NAME_MAP.get(alpha2) or c.get("common_name") or c.get("name")

            # Get official name from either mapping or field, otherwise null
            official_name = OFFICIAL_NAME_MAP.get(alpha2) or c.get("official_name", "")

            # Create and cache
            countries[alpha2] = CountryModel(
                id=id,
                name=name,
                official_name=official_name,
                alpha2=alpha2,
                alpha3=c["alpha_3"],
                numeric=c["numeric"],
                aliases=ALIAS_MAP.get(alpha2, []),
                flag=c["flag"],
            )

    return countries
