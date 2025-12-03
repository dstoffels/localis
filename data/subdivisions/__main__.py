# This script merges subdivision data from GeoNames and ISO 3166-2.
# We initialize from GeoNames and merge in the ISO data, prompting to resolve ambiguities.
# Manual intervention is required for some entries, which is mapped in src/resoluton_map.json
# villager only supports administrative levels 1 and 2, which covers most cases.

from data.utils import *
from data.subdivisions.utils import SubdivisionMap
from localis.models import CountryModel, SubdivisionModel
from .scripts.geonames import map_subdivisions
from .scripts.iso import load_iso_subs
from .scripts.merge import try_merge
from .scripts.resolve import resolve_unmatched_subs
from .scripts.dump import dump


def main():
    # Cache countries by alpha2 code
    countries: dict[str, CountryModel] = load_countries()

    # Initialize subdivision cache with geonames subdivisions into a mapping of country_alpha2 > admin_level > id.
    # SubdivisionMap also flat maps by id, geoname code and iso code
    sub_map: SubdivisionMap = map_subdivisions(countries)

    # Cache and dedupe iso subs by id
    iso_subs: dict[int, SubdivisionModel] = load_iso_subs(countries, sub_map)

    # Attempt to auto-merge with fuzzy matching and yield a list of iso_subs that couldn't be auto-matched with GeoNames counterparts.
    unmatched_iso_subs: list[SubdivisionModel] = try_merge(iso_subs, sub_map)

    # Manually match or add the dangling iso subs to the sub_map
    resolve_unmatched_subs(unmatched_iso_subs, sub_map)

    # rebuild cache with complete data, update parents
    sub_map.refresh()

    dump(sub_map)


if __name__ == "__main__":
    main()
