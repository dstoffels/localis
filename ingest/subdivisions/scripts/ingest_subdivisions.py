# This script merges subdivision data from GeoNames and ISO 3166-2, with Ipregistry
# layered in only for alias enrichment. We initialize from GeoNames and merge in the
# ISO data, prompting to resolve ambiguities. Manual intervention is required for some
# entries, which is mapped in ingest/subdivisions/outputs/resolution_map.json.
# villager only supports administrative levels 1 and 2, which covers most cases.

from ingest.shared.scripts import load_countries
from .fetch_subdivisions import fetch_subdivisions_sources
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.utils import ingest_log
from ingest.shared.models import CountryModel, SubdivisionModel
from .geonames_subdivisions import map_geonames_subdivisions
from .iso_subdivisions import load_iso_subs
from .merge_ipregistry import merge_ipregistry_aliases
from .merge_alternate_names import merge_alternate_name_aliases
from .merge_subdivisions import try_merge
from .resolve_subdivisions import resolve_unmerged_subs
from .audit_unclaimed import audit_unclaimed_geonames_subs
from .dump_subdivisions import dump


def ingest_subdivisions(
    countries: dict[str, CountryModel] = None, force: bool = False
) -> dict[str, SubdivisionModel] | None:
    ingest_log.set_stage("SUBDIVISIONS")
    try:
        has_update = fetch_subdivisions_sources(force=force)

        if not has_update:
            ingest_log.writeline("No updates for subdivisions.")
            return None

        # Cache countries by alpha2 code, unless already provided by a prior ingest stage
        if countries is None:
            countries = load_countries()

        # Initialize subdivision cache with geonames subdivisions into a mapping of country_alpha2 > admin_level > id.
        # SubdivisionMap also flat maps by id, geoname code and iso code
        sub_map: SubdivisionMap = map_geonames_subdivisions(countries)

        # Enrich GeoNames subdivisions with alternate names before merging, so the extra name variants are also available to fuzzy matching
        merge_alternate_name_aliases(sub_map)

        # Cache and dedupe iso subs by id
        iso_subs, non_administrative_subs = load_iso_subs(countries)

        # ISO-listed entries known upfront to have no GeoNames counterpart (documentation/statistical groupings, not real administrative divisions); add directly, bypassing merge entirely
        for sub in non_administrative_subs:
            sub_map.add(sub)

        # Enrich with Ipregistry's localVariant aliases; iso-codes has no alias field of its own
        merge_ipregistry_aliases(iso_subs)

        # Attempt to auto-merge with fuzzy matching and yield a list of iso_subs that couldn't be auto-matched with GeoNames counterparts.
        unmerged_iso_subs: list[SubdivisionModel] = try_merge(iso_subs, sub_map)

        # Manually match or add the dangling iso subs to the sub_map
        resolve_unmerged_subs(unmerged_iso_subs, sub_map)

        # rebuild cache with complete data, update parents
        sub_map.refresh()

        audit_unclaimed_geonames_subs(sub_map)

        dump(sub_map)
        ingest_log.writeline(f"completed: {len(sub_map)} subdivisions")
        return sub_map.to_geocode_map()
    finally:
        ingest_log.dump()
