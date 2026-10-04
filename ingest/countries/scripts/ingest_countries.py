# This script merges country data from ISO 3166-1, GeoNames and Wikidata, with ISO's values shipped as published and the latter two contributing aliases.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from .load_iso_countries import init_iso_countries
from .load_historic_countries import init_historic_countries
from .fetch_countries import fetch_countries_sources
from .merge_countries import merge_wikidata, merge_geonames, drop_ambiguous_aliases
from .wikidata_countries import COUNTRY_NAMES, fetch_wikidata_country_names
from .place_macroregions import place_macroregions
from ingest.utils import ingest_log, commit_manifest, dump_registry, COUNTRIES_MANIFEST_PATH
from ingest.utils.strings import dedupe
from ingest.shared.models import CountryModel
from ingest.macroregions.scripts import Macroregions, load_macroregions


def ingest_countries(macroregions: Macroregions | None = None, force: bool = False) -> dict[str, CountryModel] | None:
    ingest_log.set_stage("COUNTRIES")
    try:
        has_update = fetch_countries_sources(force=force)

        # the Wikidata query needs the current countries, and has no ETag, so it runs before the change check: a result that differs from the committed one is an update
        countries = init_iso_countries()
        countries = init_historic_countries(countries)
        merge_geonames(countries)
        current_alpha2s = {c.alpha2 for c in countries.values() if not c.historic}
        country_names = fetch_wikidata_country_names(current_alpha2s)
        names_changed = COUNTRY_NAMES.changed(country_names)

        # rows store macroregion ids, so macroregions rebuilt upstream (passed in) force a rebuild even when country sources are unchanged
        if not has_update and not names_changed and macroregions is None:
            ingest_log.writeline("No updates for countries, their Wikidata names or macroregions.")
            # same names, so committing only settles the file's formatting
            COUNTRY_NAMES.commit()
            return None
        if macroregions is None:
            macroregions = load_macroregions()
        merge_wikidata(countries, country_names)
        drop_ambiguous_aliases(countries)
        # curated, GeoNames and Wikidata aliases overlap, so normalize whitespace and dedupe once every source has been merged
        for country in countries.values():
            country.aliases = dedupe(country.aliases, exclude=(country.name, country.official_name or "", country.common_name or ""))
        place_macroregions(countries, macroregions)
        dump_registry("countries", list(countries.values()))
        commit_manifest(COUNTRIES_MANIFEST_PATH)
        COUNTRY_NAMES.commit()
        ingest_log.writeline(f"completed: {len(countries)} countries")
        return countries
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_countries(force=True)
