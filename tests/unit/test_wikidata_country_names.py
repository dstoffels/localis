import pytest
from ingest.countries.scripts.merge_countries import _wikidata_alias, drop_ambiguous_aliases
from ingest.shared.models import CountryModel

ISO_CODES = {"GB", "GBR", "CA", "CAN", "CD", "COD", "TW", "TWN"}


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("the UK", "UK"),
        ("the United Kingdom", "United Kingdom"),
        ("DRC", "DRC"),
        ("ROC", "ROC"),
        ("U.S.", "U.S."),
        ("Congo (Kinshasa)", "Congo (Kinshasa)"),
        ("  Faeroe   Islands ", "Faeroe Islands"),
        ("CAN", None),
        ("TWN", None),
        ("el", None),
        ("zaf", None),
        ("U K", None),
        ("ISO 3166-1:BH", None),
        ("+256", None),
        ("Republic of Upper Volta (-1984)", None),
        ("Atlantic/Faroe", None),
        ("🇫🇴", None),
        ("the", None),
        ("GB-GSY", None),
        ("US-GU", None),
        ("Հայաստան", None),
        ("Curaςao", None),
        ("Côte d'Ivoire", "Côte d'Ivoire"),
    ],
)
def test_wikidata_alias(raw: str, expected: str | None):
    """Wikidata names are kept as aliases only when they're names, not identifiers, codes or noise"""
    assert _wikidata_alias(raw, ISO_CODES) == expected


def test_wikidata_alias_drops_item_codes():
    """an item's own IOC/FIFA codes are codes, not names, even though they look like abbreviations"""
    assert _wikidata_alias("CHI", ISO_CODES, {"CHI"}) is None
    assert _wikidata_alias("DRC", ISO_CODES, {"COD"}) == "DRC"


def _country(alpha2: str, name: str, aliases: list[str], historic: str | None = None) -> CountryModel:
    return CountryModel(
        id=0, name=name, alpha2=alpha2, alpha3=None, geonames_id=None, official_name=None, common_name=None,
        aliases=aliases, numeric=None, flag=None, historic=historic,
    )


def test_drop_ambiguous_aliases():
    """an alias another current country also has as a name or alias is dropped from both; historic entries don't count"""
    countries = {
        "MF": _country("MF", "Saint Martin (French part)", ["Saint-Martin", "Collectivity of Saint Martin"]),
        "SX": _country("SX", "Sint Maarten (Dutch part)", ["St. Martin", "Sint Maarten"]),
        "TL": _country("TL", "Timor-Leste", ["East Timor"]),
        "TPTL": _country("TP", "East Timor", [], historic="TPTL|2002-05-20|"),
    }
    drop_ambiguous_aliases(countries)
    assert countries["MF"].aliases == ["Collectivity of Saint Martin"]
    assert countries["SX"].aliases == ["Sint Maarten"]
    assert countries["TL"].aliases == ["East Timor"]
