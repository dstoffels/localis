# This script merges subdivision data from GeoNames and ISO 3166-2.
# We initialize from GeoNames and merge in the ISO data, prompting to resolve ambiguities.
# Manual intervention is required for some entries, which is mapped in src/resoluton_map.json
# villager only supports administrative levels 1 and 2, which covers most cases.

from data.utils import *
from data.subdivisions.scripts.fetch_subdivisions import fetch_subdivisions_sources
from data.subdivisions.subdivisions_utils import SubdivisionMap
from data.logger import log
from localis.models import CountryModel, SubdivisionModel
from .scripts.geonames_subdivisions import map_geonames_subdivisions
from .scripts.iso_subdivisions import load_iso_subs
from .scripts.merge_subdivisions import try_merge
from .scripts.resolve_subdivisions import resolve_unmatched_subs
from .scripts.dump_subdivisions import dump


def ingest_subdivisions(
    countries: dict[str, CountryModel] = None,
    interactive_mode: bool = False,
) -> SubdivisionMap:
    log.set_stage("SUBDIVISIONS")
    fetch_subdivisions_sources()

    # Cache countries by alpha2 code, unless already provided by a prior ingest stage
    if countries is None:
        countries = load_countries()

    # Initialize subdivision cache with geonames subdivisions into a mapping of country_alpha2 > admin_level > id.
    # SubdivisionMap also flat maps by id, geoname code and iso code
    sub_map: SubdivisionMap = map_geonames_subdivisions(countries)

    # Cache and dedupe iso subs by id
    iso_subs: dict[int, SubdivisionModel] = load_iso_subs(countries, sub_map)

    # Attempt to auto-merge with fuzzy matching and yield a list of iso_subs that couldn't be auto-matched with GeoNames counterparts.
    unmatched_iso_subs: list[SubdivisionModel] = try_merge(iso_subs, sub_map)

    # Manually match or add the dangling iso subs to the sub_map
    orphaned_subs = resolve_unmatched_subs(
        unmatched_iso_subs, sub_map, interactive_mode
    )
    for orphan in orphaned_subs:
        log.writeline(
            f"orphaned: {orphan.iso_code} ({orphan.name}, {orphan.country.name}) - no fuzzy match, requires manual resolution."
        )

    # rebuild cache with complete data, update parents
    sub_map.refresh()

    dump(sub_map)
    log.writeline(
        f"completed: {len(sub_map)} subdivisions, {len(orphaned_subs)} orphaned"
    )
    return sub_map


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    ingest_subdivisions(interactive_mode=args.interactive)
