# This script merges country data from ISO 3166-1, GeoNames and Wikidata, with ISO's values shipped as published and the latter two contributing aliases.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from .load_iso_countries import init_iso_countries
from .load_historic_countries import init_historic_countries
from .fetch_countries import fetch_countries_sources
from .merge_countries import merge_wikidata, merge_geonames, drop_ambiguous_aliases
from .wikidata_countries import fetch_wikidata_country_names
from .dump_countries import dump
from ingest.utils import ingest_log, commit_manifest, COUNTRIES_MANIFEST_PATH
from ingest.utils.strings import dedupe
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
        merge_wikidata(countries, fetch_wikidata_country_names())
        drop_ambiguous_aliases(countries)
        # curated, GeoNames and Wikidata aliases overlap, so normalize whitespace and dedupe once every source has been merged
        for country in countries.values():
            country.aliases = dedupe(country.aliases, exclude=(country.name, country.official_name or "", country.common_name or ""))
        dump(list(countries.values()))
        commit_manifest(COUNTRIES_MANIFEST_PATH)
        ingest_log.writeline(f"completed: {len(countries)} countries")
        return countries
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_countries(force=True)
