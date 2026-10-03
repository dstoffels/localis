# This script initializes the dataset from ISO 3166-1, whose names are shipped exactly as published, plus curated aliases.
# These will be merged with data from their GeoNames and Wikipedia counterparts.

from ingest.utils import COUNTRIES_INPUTS_PATH, ingest_log
from ingest.shared.models import CountryModel
import json


def init_iso_countries() -> dict[str, CountryModel]:
    """Parses country data from ISO 3166-1 and returns an alpha2 mapped cache"""
    ingest_log.writeline("Loading ISO countries...")
    countries: dict[str, CountryModel] = {}

    # curated alternate names, not merged (see aliases below); kept for review until each is either sourced or dropped
    ALIAS_MAP = {
        "GB": [
            "Great Britain",
            "Britain",
            "UK",
        ],
        "US": ["America"],
        "CI": ["Ivory Coast", "Cote d'Ivoire"],
        "MM": ["Burma"],
        "SZ": ["Swaziland"],
        "NL": ["Holland"],
        "MK": ["Macedonia"],
        "CV": ["Cape Verde"],
        "SY": ["Syria"],
        "RU": ["Russia"],
        "VN": ["Vietnam", "Viet Nam"],
        "CG": ["Republic of the Congo", "Congo-Brazzaville", "Congo Republic"],
        "CD": [
            "Democratic Republic of the Congo",
            "DRC",
            "Congo-Kinshasa",
            "DR Congo",
            "Zaire",
        ],
        "BN": ["Brunei"],
        "ST": ["São Tomé and Príncipe"],
        "TL": ["East Timor"],
        "BQ": ["Caribbean Netherlands"],
        "SX": [
            "Sint Maarten",
            "Country of Sint Maarten",
            "Land Sint Maarten",
            "Dutch Sint Maarten",
        ],
        "MF": [
            "Saint-Martin",
            "Collectivity of Saint Martin",
            "Collectivité de Saint-Martin",
        ],
        "TW": ["Republic of China", "ROC"],
        "FK": ["Falkland Islands"],
        "FM": ["Micronesia"],
        "PS": ["Palestine"],
        "SH": ["Saint Helena"],
        "VA": ["Holy See", "Vatican City State"],
        "VG": ["British Virgin Islands"],
        "VI": ["U.S. Virgin Islands"],
        "KR": ["Republic of Korea"],
    }

    with open(COUNTRIES_INPUTS_PATH / "iso_3166-1.json", "r", encoding="utf-8") as f:
        iso_countries: list[dict] = json.load(f).get("3166-1")
        iso_countries.sort(key=lambda c: c.get("alpha_2") or "")

        for id, c in enumerate(iso_countries, 1):
            alpha2 = c["alpha_2"]
            countries[alpha2] = CountryModel(
                id=id,
                name=c["name"],
                official_name=c.get("official_name"),
                # common_name is iso-codes' addition, not part of ISO 3166-1, so it's kept in its own field
                common_name=c.get("common_name"),
                alpha2=alpha2,
                alpha3=c["alpha_3"],
                geonames_id=None,
                numeric=c["numeric"],
                # ALIAS_MAP is no longer merged while its aliases are reviewed against what GeoNames and Wikidata already supply
                aliases=[],
                flag=c["flag"],
                historic=None,
            )

    return countries
