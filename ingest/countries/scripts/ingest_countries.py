# This stage merges country data from ISO 3166-1, GeoNames and Wikidata, with ISO's values shipped as published and the latter two contributing aliases; CLDR places them in macroregions and gives their currencies and languages.
# GeoNames' alternateNames.txt is not used since the names tend to be noisy and mainly historical.

from .load_iso_countries import init_iso_countries
from .load_historic_countries import init_historic_countries
from .fetch_countries import fetch_countries_sources
from .merge_countries import merge_wikidata, merge_geonames, drop_ambiguous_aliases
from .wikidata_countries import COUNTRY_NAMES, fetch_wikidata_country_names
from .place_macroregions import place_macroregions
from .place_currencies import place_currencies
from .place_languages import place_languages
from ingest.utils import COUNTRIES, ingest_log, dump_registry
from ingest.utils.strings import dedupe
from ingest.shared.models import CountryModel, CurrencyModel, LanguageModel, ScriptModel
from ingest.macroregions.scripts import Macroregions


def ingest_countries(
    macroregions: Macroregions,
    currencies: dict[str, CurrencyModel],
    scripts: dict[str, ScriptModel],
    languages: dict[str, LanguageModel],
) -> dict[str, CountryModel]:
    with ingest_log.stage(COUNTRIES):
        fetch_countries_sources()
        countries = init_iso_countries()
        countries = init_historic_countries(countries)
        merge_geonames(countries)
        # the Wikidata query needs the current countries
        current_alpha2s = {c.alpha2 for c in countries.values() if not c.historic}
        country_names = fetch_wikidata_country_names(current_alpha2s)
        COUNTRY_NAMES.log_changes(country_names)
        merge_wikidata(countries, country_names)
        drop_ambiguous_aliases(countries)
        # curated, GeoNames and Wikidata aliases overlap, so normalize whitespace and dedupe once every source has been merged
        for country in countries.values():
            country.aliases = dedupe(country.aliases, exclude=(country.name, country.official_name or "", country.common_name or ""))
        place_macroregions(countries, macroregions)
        place_currencies(countries, currencies)
        place_languages(countries, languages, scripts)
        dump_registry("countries", list(countries.values()))
        ingest_log.writeline(f"completed: {len(countries)} countries")
        return countries
