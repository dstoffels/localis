# This script merges subdivision data from GeoNames and ISO 3166-2.
# We initialize from GeoNames and merge in the ISO data, prompting to resolve ambiguities.
# Manual intervention is required for some entries, which is mapped in src/resoluton_map.json
# villager only supports administrative levels 1 and 2, which covers most cases.

from ingest.countries.scripts import load_countries
from .fetch_subdivisions import fetch_subdivisions_sources
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.utils import log
from ingest.countries import CountryModel
from ingest.subdivisions import SubdivisionModel
from .geonames_subdivisions import map_geonames_subdivisions
from .iso_subdivisions import load_iso_subs
from .merge_subdivisions import try_merge
from .resolve_subdivisions import resolve_unmerged_subs
from .dump_subdivisions import dump


def ingest_subdivisions(
    countries: dict[str, CountryModel] = None, force: bool = False
) -> dict[str, SubdivisionModel] | None:
    log.set_stage("SUBDIVISIONS")
    has_update = fetch_subdivisions_sources(force=force)

    if not has_update:
        log.writeline("No updates for subdivisions.")
        return None

    # Cache countries by alpha2 code, unless already provided by a prior ingest stage
    if countries is None:
        countries = load_countries()

    # Initialize subdivision cache with geonames subdivisions into a mapping of country_alpha2 > admin_level > id.
    # SubdivisionMap also flat maps by id, geoname code and iso code
    sub_map: SubdivisionMap = map_geonames_subdivisions(countries)

    # Cache and dedupe iso subs by id
    iso_subs: dict[int, SubdivisionModel] = load_iso_subs(countries)

    # Attempt to auto-merge with fuzzy matching and yield a list of iso_subs that couldn't be auto-matched with GeoNames counterparts.
    unmerged_iso_subs: list[SubdivisionModel] = try_merge(iso_subs, sub_map)

    # Manually match or add the dangling iso subs to the sub_map
    resolve_unmerged_subs(unmerged_iso_subs, sub_map)

    # rebuild cache with complete data, update parents
    sub_map.refresh()

    dump(sub_map)
    log.writeline(f"completed: {len(sub_map)} subdivisions")
    return sub_map.to_geocode_map()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Deprecated: use the resolve-subdivisions skill instead.",
    )
    args = parser.parse_args()
    ingest_subdivisions(interactive_mode=args.interactive)
