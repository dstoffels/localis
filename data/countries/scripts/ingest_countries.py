# This script merges country data from ISO 3166-1, Wikidata and GeoNames, with ISO as the source of truth and the latter two for alternate names/aliases.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from data.countries.scripts.load_iso_countries import init_iso_countries
from data.countries.scripts.fetch_countries import fetch_countries_sources
from data.countries.scripts.merge_countries import merge_wikidata, merge_geonames
from data.countries.scripts.dump_countries import dump
from data.utils.logger import log
from localis.models import CountryModel


def ingest_countries(force: bool = False) -> dict[str, CountryModel] | None:
    log.set_stage("COUNTRIES")
    has_update = fetch_countries_sources(force=force)
    if not has_update:
        log.writeline("No updates for countries.")
        return None
    countries = init_iso_countries()
    merge_geonames(countries)
    merge_wikidata(countries)
    dump(list(countries.values()))
    log.writeline(f"completed: {len(countries)} countries")
    return countries


if __name__ == "__main__":
    ingest_countries(force=True)
