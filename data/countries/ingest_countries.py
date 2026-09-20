# This script merges country data from ISO 3166-1, Wikidata and GeoNames, with ISO as the source of truth and the latter two for alternate names/aliases.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from data.countries.scripts.load_iso_countries import init_iso_countries
from data.countries.scripts.fetch_countries import fetch_countries_sources
from data.countries.scripts.merge_countries import merge_wikidata, merge_geonames
from data.countries.scripts.dump_countries import dump
from data.logger import log
from localis.models import CountryModel


def ingest_countries() -> dict[str, CountryModel]:
    log.set_stage("COUNTRIES")
    fetch_countries_sources()
    countries = init_iso_countries()
    merge_wikidata(countries)
    merge_geonames(countries)
    dump(list(countries.values()))
    log.writeline(f"completed: {len(countries)} countries")
    return countries


if __name__ == "__main__":
    ingest_countries()
