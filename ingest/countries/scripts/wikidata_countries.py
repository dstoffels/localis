import json
import urllib.parse
import urllib.request
from ingest.utils import COUNTRIES_INPUTS_PATH, ingest_log

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# every item with an ISO 3166-1 alpha-2 code (P297): its English label, alternative labels and short names (P1813), its IOC (P984) and FIFA (P3441) codes, which appear among the alternative labels but aren't names, and its sitelink count to pick between items sharing a code
SPARQL_QUERY = """
SELECT ?iso ?item ?sitelinks ?label ?alt ?short ?ioc ?fifa WHERE {
  ?item wdt:P297 ?iso ;
        wikibase:sitelinks ?sitelinks .
  OPTIONAL { ?item rdfs:label ?label FILTER(LANG(?label) = "en") }
  OPTIONAL { ?item skos:altLabel ?alt FILTER(LANG(?alt) = "en") }
  OPTIONAL { ?item wdt:P1813 ?short FILTER(LANG(?short) = "en") }
  OPTIONAL { ?item wdt:P984 ?ioc }
  OPTIONAL { ?item wdt:P3441 ?fifa }
}
"""
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"
COUNTRY_NAMES_PATH = COUNTRIES_INPUTS_PATH / "wikidata_country_names.json"


def fetch_wikidata_country_names() -> dict[str, dict[str, list[str]]]:
    """English names and sports codes of every ISO alpha-2 country from Wikidata, keyed by alpha-2 as {"names": [...], "codes": [...]}, fetched live and persisted to inputs/."""
    url = (
        SPARQL_ENDPOINT + "?query=" + urllib.parse.quote(SPARQL_QUERY) + "&format=json"
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    ingest_log.writeline("Querying Wikidata for country names...")
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    items: dict[str, dict[str, tuple[int, set[str], set[str]]]] = {}
    for binding in data["results"]["bindings"]:
        iso = binding["iso"]["value"]
        item = binding["item"]["value"].rsplit("/", 1)[1]
        _, names, codes = items.setdefault(iso, {}).setdefault(
            item, (int(binding["sitelinks"]["value"]), set(), set())
        )
        for field in ("label", "alt", "short"):
            if field in binding:
                names.add(binding[field]["value"])
        for field in ("ioc", "fifa"):
            if field in binding:
                codes.add(binding[field]["value"])

    # a code claimed by several items keeps the one with the most sitelinks: Cyprus over a same-named item, Antarctica over the Antarctic Treaty area
    country_names: dict[str, dict[str, list[str]]] = {}
    for iso, by_item in sorted(items.items()):
        _, names, codes = max(by_item.values(), key=lambda entry: entry[0])
        country_names[iso] = {"names": sorted(names), "codes": sorted(codes)}
    COUNTRY_NAMES_PATH.write_text(
        json.dumps(country_names, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return country_names
