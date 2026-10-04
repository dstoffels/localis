# This script merges country data from ISO 3166-1, GeoNames and Wikidata, with ISO's values shipped as published and the latter two contributing aliases; CLDR places them in macroregions and gives their currencies and languages.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from .load_iso_countries import init_iso_countries
from .load_historic_countries import init_historic_countries
from .fetch_countries import fetch_countries_sources
from .merge_countries import merge_wikidata, merge_geonames, drop_ambiguous_aliases
from .wikidata_countries import COUNTRY_NAMES, fetch_wikidata_country_names
from .place_macroregions import place_macroregions
from .place_currencies import place_currencies
from .place_languages import place_languages
from ingest.utils import ingest_log, commit_manifest, dump_registry, COUNTRIES_MANIFEST_PATH
from ingest.utils.strings import dedupe
from ingest.shared.models import CountryModel, CurrencyModel, LanguageModel, ScriptModel
from ingest.macroregions.scripts import Macroregions, load_macroregions
from ingest.currencies.scripts import load_currencies
from ingest.scripts.scripts import load_scripts
from ingest.languages.scripts import load_languages


def ingest_countries(
    macroregions: Macroregions | None = None,
    currencies: dict[str, CurrencyModel] | None = None,
    scripts: dict[str, ScriptModel] | None = None,
    languages: dict[str, LanguageModel] | None = None,
    force: bool = False,
) -> dict[str, CountryModel] | None:
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

        # rows store macroregion, currency, language and script ids, so any of them rebuilt upstream (passed in) forces a rebuild even when country sources are unchanged
        upstream = (macroregions, currencies, scripts, languages)
        if not has_update and not names_changed and all(u is None for u in upstream):
            ingest_log.writeline("No updates for countries, their Wikidata names, macroregions, currencies, scripts or languages.")
            # same names, so committing only settles the file's formatting
            COUNTRY_NAMES.commit()
            return None
        if macroregions is None:
            macroregions = load_macroregions()
        if currencies is None:
            currencies = load_currencies()
        if scripts is None:
            scripts = load_scripts()
        if languages is None:
            languages = load_languages(scripts)
        merge_wikidata(countries, country_names)
        drop_ambiguous_aliases(countries)
        # curated, GeoNames and Wikidata aliases overlap, so normalize whitespace and dedupe once every source has been merged
        for country in countries.values():
            country.aliases = dedupe(country.aliases, exclude=(country.name, country.official_name or "", country.common_name or ""))
        place_macroregions(countries, macroregions)
        place_currencies(countries, currencies)
        place_languages(countries, languages, scripts)
        dump_registry("countries", list(countries.values()))
        commit_manifest(COUNTRIES_MANIFEST_PATH)
        COUNTRY_NAMES.commit()
        ingest_log.writeline(f"completed: {len(countries)} countries")
        return countries
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_countries(force=True)
