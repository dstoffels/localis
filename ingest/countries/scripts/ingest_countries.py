# This script merges country data from ISO 3166-1, Wikidata and GeoNames, with ISO as the source of truth and the latter two for alternate names/aliases.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from .load_iso_countries import init_iso_countries
from .load_historic_countries import init_historic_countries
from .fetch_countries import fetch_countries_sources
from .merge_countries import merge_wikidata, merge_geonames
from .dump_countries import dump
from ingest.utils import ingest_log
from ingest.shared.models import CountryModel


def ingest_countries(force: bool = False) -> dict[str, CountryModel] | None:
    ingest_log.set_stage("COUNTRIES")
    try:
        has_update = fetch_countries_sources(force=force)
        if not has_update:
            ingest_log.writeline("No updates for countries.")
            return None
        countries = init_iso_countries()
        countries = init_historic_countries(countries)
        merge_geonames(countries)
        merge_wikidata(countries)
        dump(list(countries.values()))
        ingest_log.writeline(f"completed: {len(countries)} countries")
        return countries
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_countries(force=True)
