# This script builds CLDR's macroregions (regions, subregions and groupings) from its territory containment and English territory names.

from .fetch_macroregions import fetch_macroregions_sources
from .load_macroregions import load_macroregions, Macroregions
from ingest.utils import ingest_log, commit_manifest, dump_registry, MACROREGIONS_MANIFEST_PATH


def ingest_macroregions(force: bool = False) -> Macroregions | None:
    ingest_log.set_stage("MACROREGIONS")
    try:
        has_update = fetch_macroregions_sources(force=force)
        if not has_update:
            ingest_log.writeline("No updates for macroregions.")
            return None
        macroregions = load_macroregions()
        dump_registry("macroregions", macroregions.all, queryable=False)
        commit_manifest(MACROREGIONS_MANIFEST_PATH)
        ingest_log.writeline(f"completed: {len(macroregions.all)} macroregions")
        return macroregions
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_macroregions(force=True)
