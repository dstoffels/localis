# This stage builds CLDR's macroregions (regions, subregions and groupings) from its territory containment and English territory names.

from .fetch_macroregions import fetch_macroregions_sources
from .load_macroregions import load_macroregions, Macroregions
from ingest.utils import MACROREGIONS, ingest_log, dump_registry


def ingest_macroregions() -> Macroregions:
    with ingest_log.stage(MACROREGIONS):
        fetch_macroregions_sources()
        macroregions = load_macroregions()
        dump_registry("macroregions", macroregions.all, queryable=False)
        ingest_log.writeline(f"completed: {len(macroregions.all)} macroregions")
        return macroregions
