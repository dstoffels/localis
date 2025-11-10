# This script parses geonames' allCountries.txt into a filtered TSV of cities with enriched data for country, subdivision and alternate city names as search tokens.
# Country and subdivision data are loaded from separate TSV files.
# Cities are filtered based on feature codes and population. We only want to include actual populated settlements as allCountries.txt contains many other geographical features.
# allCountries.txt (1.64GB) must be manually downloaded to the src folder from https://download.geonames.org/export/dump/

from .scripts.utils import *
from .scripts.load import load_cities
from .scripts.dump import dump_to_tsv
import json
import re


def main():
    countries: dict[str, str] = load_countries()
    subdivisions: dict[str, str] = load_subdivisions()
    cities: list[CityDTO] = load_cities(subdivisions, countries)
    dump_to_tsv(cities)


# def parse_tokens(alt_names: str, name: str) -> str:
#     STOPWORDS = {"the", "of", "and"}

#     tokens: set[str] = set()

#     names = alt_names.split("|")

#     for n in names:
#         parts = n.lower().strip().split()
#         for p in parts:
#             if p not in name.lower().split() and p not in STOPWORDS and len(p) > 2:
#                 tokens.add(p)

#     return " ".join(sorted(tokens))


if __name__ == "__main__":
    main()
