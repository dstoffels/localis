import json
import urllib.parse
import urllib.request
from ingest.utils import SUBDIVISIONS_INPUTS_PATH, ingest_log
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.shared.models import SubdivisionModel
from .automerge import merge_matched_sub

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
SPARQL_QUERY = """
SELECT ?isoCode ?geonamesId WHERE {
  ?item wdt:P300 ?isoCode .
  ?item wdt:P1566 ?geonamesId .
}
"""
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"
CROSSWALK_PATH = SUBDIVISIONS_INPUTS_PATH / "wikidata_crosswalk.json"


def fetch_wikidata_crosswalk() -> dict[str, int]:
    """Queries Wikidata for every (P300 ISO 3166-2 code, P1566 GeoNames id) pair, keeping only unambiguous ISO codes (exactly one distinct geonames_id claimed). Persists the raw crosswalk to inputs/ for inspection, but always re-fetches live rather than checksum-gating, since this is a derived query result, not a stable file with its own ETag."""
    url = SPARQL_ENDPOINT + "?query=" + urllib.parse.quote(SPARQL_QUERY) + "&format=json"
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"}
    )
    ingest_log.writeline("Querying Wikidata for ISO/GeoNames crosswalk...")
    with urllib.request.urlopen(request, timeout=120) as response:
        data = json.loads(response.read().decode("utf-8"))

    by_iso_code: dict[str, set[int]] = {}
    for binding in data["results"]["bindings"]:
        iso_code = binding["isoCode"]["value"]
        geonames_id = int(binding["geonamesId"]["value"])
        by_iso_code.setdefault(iso_code, set()).add(geonames_id)

    crosswalk = {code: next(iter(ids)) for code, ids in by_iso_code.items() if len(ids) == 1}

    CROSSWALK_PATH.write_text(
        json.dumps(crosswalk, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return crosswalk


def apply_wikidata_matches(
    iso_subs: dict[str, SubdivisionModel],
    resolution_map: ResolutionMap,
    sub_map: SubdivisionMap,
) -> dict[str, SubdivisionModel]:
    """Applies unambiguous Wikidata crosswalk matches for whatever skill_resolved didn't already claim, before auto-merge ever sees these iso_subs. Recomputed fresh every run (external data we don't control, not a one-time human decision) and reconciled against `audited`."""
    crosswalk = fetch_wikidata_crosswalk()
    resolution_map.wikidata_merge = {}
    remaining: dict[str, SubdivisionModel] = {}

    for iso_code, iso_sub in iso_subs.items():
        geonames_id = crosswalk.get(iso_code)
        if geonames_id is None:
            remaining[iso_code] = iso_sub
            continue

        mapped_sub = sub_map.get(geonames_id=geonames_id)
        if mapped_sub is None or mapped_sub.country.alpha2 != iso_sub.country.alpha2:
            remaining[iso_code] = iso_sub
            continue

        if mapped_sub.iso_code and mapped_sub.iso_code != iso_code:
            ingest_log.writeline(
                f"wikidata conflict: {iso_code} '{iso_sub.name}'s target {mapped_sub.geonames_code} '{mapped_sub.name}' is already claimed by {mapped_sub.iso_code}",
                level="WARN",
            )
            remaining[iso_code] = iso_sub
            continue

        if not resolution_map.reconcile(iso_code, geonames_id):
            resolution_map.wikidata_merge[iso_code] = geonames_id
        merge_matched_sub(iso_sub, mapped_sub)

    resolved_count = len(iso_subs) - len(remaining)
    ingest_log.writeline(
        f"resolved {resolved_count}/{len(iso_subs)} subdivisions from Wikidata crosswalk"
    )
    return remaining
