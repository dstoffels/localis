from dataclasses import dataclass, field
from ingest.utils import COUNTRIES, CommittedQuery, ingest_log, sparql

# an item's English label, alternative labels and short names (P1813), and its IOC (P984) and FIFA (P3441) codes, which appear among the alternative labels but aren't names
_NAME_FIELDS = """
  OPTIONAL { ?item rdfs:label ?label FILTER(LANG(?label) = "en") }
  OPTIONAL { ?item skos:altLabel ?alt FILTER(LANG(?alt) = "en") }
  OPTIONAL { ?item wdt:P1813 ?short FILTER(LANG(?short) = "en") }
  OPTIONAL { ?item wdt:P984 ?ioc }
  OPTIONAL { ?item wdt:P3441 ?fifa }
"""
# every item with an ISO 3166-1 alpha-2 code (P297), with its sitelink count to pick between items sharing a code
CURRENT_QUERY = f"""
SELECT ?code ?item ?sitelinks ?label ?alt ?short ?ioc ?fifa WHERE {{
  ?item wdt:P297 ?code ;
        wikibase:sitelinks ?sitelinks .
{_NAME_FIELDS}}}
"""
# every item with an ISO 3166-3 alpha-4 code (P773), with any alpha-2 it also holds, which marks the item of a country that still exists
HISTORIC_QUERY = f"""
SELECT ?code ?item ?alpha2 ?label ?alt ?short ?ioc ?fifa WHERE {{
  ?item wdt:P773 ?code .
  OPTIONAL {{ ?item wdt:P297 ?alpha2 }}
{_NAME_FIELDS}}}
"""
CountryEntry = dict[str, list[str]]
CountryNames = dict[str, CountryEntry]

# committed as the names' provenance; changes need no review beyond the ingest PR, whose countries.tsv diff shows their effect
COUNTRY_NAMES = CommittedQuery[CountryEntry](COUNTRIES.inputs / "wikidata_country_names.json", "Wikidata country names")


@dataclass
class _Item:
    sitelinks: int = 0
    names: set[str] = field(default_factory=set)
    codes: set[str] = field(default_factory=set)
    alpha2s: set[str] = field(default_factory=set)


def _items_by_code(query: str) -> dict[str, dict[str, _Item]]:
    """Each queried code's items, keyed by Wikidata id, with their names, sports codes and alpha-2 codes."""
    items: dict[str, dict[str, _Item]] = {}
    for binding in sparql(query):
        item_id = binding["item"]["value"].rsplit("/", 1)[1]
        item = items.setdefault(binding["code"]["value"], {}).setdefault(item_id, _Item())
        if "sitelinks" in binding:
            item.sitelinks = int(binding["sitelinks"]["value"])
        for name_field in ("label", "alt", "short"):
            if name_field in binding:
                item.names.add(binding[name_field]["value"])
        for code_field in ("ioc", "fifa"):
            if code_field in binding:
                item.codes.add(binding[code_field]["value"])
        if "alpha2" in binding:
            item.alpha2s.add(binding["alpha2"]["value"])
    return items


def _entry(items: list[_Item]) -> dict[str, list[str]]:
    return {"names": sorted(set().union(*(i.names for i in items))), "codes": sorted(set().union(*(i.codes for i in items)))}


def _query_country_names(current_alpha2s: set[str]) -> CountryNames:
    """English names and sports codes from Wikidata, keyed by alpha-2 for current countries and by ISO 3166-3 alpha-4 for historic ones, as {"names": [...], "codes": [...]}."""
    country_names: CountryNames = {}

    # a code claimed by several items keeps the one with the most sitelinks: Cyprus over a same-named item, Antarctica over the Antarctic Treaty area
    for code, by_item in sorted(_items_by_code(CURRENT_QUERY).items()):
        country_names[code] = _entry([max(by_item.values(), key=lambda item: item.sitelinks)])

    # every item holding an alpha-4 names that entry (YUCS: both Yugoslav federations), except a current country's own item, which keeps its old code (BUMM on Myanmar), whose names belong to the current country
    for code, by_item in sorted(_items_by_code(HISTORIC_QUERY).items()):
        items = [item for item in by_item.values() if not item.alpha2s & current_alpha2s]
        if items:
            country_names[code] = _entry(items)
    return country_names


def fetch_wikidata_country_names(current_alpha2s: set[str]) -> CountryNames:
    """Queries the country names and stages them for COUNTRY_NAMES.commit()."""
    ingest_log.writeline("Querying Wikidata for country names...")
    return COUNTRY_NAMES.fetch(lambda: _query_country_names(current_alpha2s))
