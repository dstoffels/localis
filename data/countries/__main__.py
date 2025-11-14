# This script merges country data from ISO 3166-1, Wikidata and GeoNames, with ISO as the source of truth and the latter two for alternate names/aliases.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from .scripts.utils import *
from .scripts.load import init_iso_countries
from .scripts.merge import merge_wikidata, merge_geonames
from .scripts.dump import dump_to_tsv


def main():
    countries = init_iso_countries()
    merge_wikidata(countries)
    merge_geonames(countries)
    dump_to_tsv(countries)


if __name__ == "__main__":
    main()
