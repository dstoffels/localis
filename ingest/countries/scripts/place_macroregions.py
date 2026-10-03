from ingest.macroregions.scripts import Macroregions
from ingest.shared.models import CountryModel
from ingest.utils import ingest_log


def place_macroregions(countries: dict[str, CountryModel], macroregions: Macroregions) -> None:
    """Sets each country's CLDR path and groupings; a historic country takes only a deprecated placement no other historic entry shares."""
    ingest_log.writeline("Placing countries in macroregions...")
    historic_by_alpha2: dict[str, list[CountryModel]] = {}

    for country in countries.values():
        # historic entries reuse current alpha2 codes, so the main tree would give them another country's placement
        if country.historic:
            historic_by_alpha2.setdefault(country.alpha2, []).append(country)
            continue
        subregion = macroregions.subregion_of.get(country.alpha2)
        if subregion is None or subregion.parent is None:
            raise ValueError(f"CLDR places {country.alpha2} ({country.name}) in no subregion")
        country.macroregions = [subregion.parent, subregion]
        country.groupings = sorted(macroregions.groupings_of.get(country.alpha2, []), key=lambda m: m.id)

    placed_historic = 0
    for alpha2, entries in historic_by_alpha2.items():
        subregions = macroregions.deprecated_subregions_of.get(alpha2, [])
        if len(entries) == 1 and len(subregions) == 1 and subregions[0].parent is not None:
            entries[0].macroregions = [subregions[0].parent, subregions[0]]
            placed_historic += 1

    historic_count = sum(len(entries) for entries in historic_by_alpha2.values())
    ingest_log.writeline(f"placed {len(countries) - historic_count} current and {placed_historic} of {historic_count} historic countries")
