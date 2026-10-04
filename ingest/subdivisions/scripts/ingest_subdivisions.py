# Merges ISO 3166-2 subdivisions into GeoNames': skill decisions, the Wikidata crosswalk and automerge in turn, with what's left recorded in outputs/resolution_map.json for the resolve-subdivisions skill.

import sys
from ingest.shared.scripts import load_countries
from .fetch_subdivisions import fetch_subdivisions_sources
from ingest.subdivisions.utils.subdivision_map import SubdivisionMap
from ingest.subdivisions.utils.resolution_map import ResolutionMap
from ingest.utils import (
    ingest_log,
    SUBDIVISIONS_OUTPUTS_PATH,
    SUBDIVISIONS_MANIFEST_PATH,
    SHARED_MANIFEST_PATH,
    record_pending,
    committed_value,
    commit_manifest,
    dump_registry,
)
from ingest.shared.models import CountryModel, SubdivisionModel
from .geonames_subdivisions import map_geonames_subdivisions
from .iso_subdivisions import load_iso_subs
from .merge_alternate_names import merge_alternate_name_aliases
from .automerge import try_merge
from .resolve_subdivisions import apply_skill_decisions
from .wikidata_subdivisions import (
    fetch_wikidata_crosswalk,
    committed_crosswalk,
    commit_crosswalk,
    log_crosswalk_changes,
    flag_wikidata_conflicts,
    apply_wikidata_matches,
)
from .non_administrative import apply_non_administrative, flag_grouping_twin_merges
from .dump_unmerged import write as write_unmerged_doc

RESOLUTION_MAP_PATH = SUBDIVISIONS_OUTPUTS_PATH / "resolution_map.json"
DECISIONS_MANIFEST_KEY = "resolution_map"


def exit_if_orphans(resolution_map: ResolutionMap | None = None) -> None:
    """Hard gate: active orphans mean the dataset is incomplete, so stop with exit code 10 until the resolve-subdivisions skill resolves them."""
    if resolution_map is None:
        resolution_map = ResolutionMap.load(RESOLUTION_MAP_PATH)
    orphans = resolution_map.automerge.orphans
    if not orphans.count():
        return
    ingest_log.writeline(
        f"BLOCKED: {orphans.count()} active orphan(s) in resolution_map.json ({orphans.summary()}); "
        "run the resolve-subdivisions skill first",
        level="WARN",
    )
    ingest_log.dump()
    sys.exit(10)


def ingest_subdivisions(
    countries: dict[str, CountryModel] | None = None, force: bool = False
) -> dict[str, SubdivisionModel] | None:
    ingest_log.set_stage("SUBDIVISIONS")
    try:
        has_update = fetch_subdivisions_sources(force=force)

        # the map's bypass rules and skill decisions are tracked like a source, so editing them triggers a rebuild without --force
        resolution_map = ResolutionMap.load(RESOLUTION_MAP_PATH)
        decisions = resolution_map.decisions_fingerprint()
        decisions_changed = decisions != committed_value(SUBDIVISIONS_MANIFEST_PATH, DECISIONS_MANIFEST_KEY)

        # the Wikidata crosswalk has no ETag, so the committed file is its record: a result that differs from it is an update
        crosswalk = fetch_wikidata_crosswalk()
        committed = committed_crosswalk()
        crosswalk_changed = crosswalk != committed
        if crosswalk_changed:
            log_crosswalk_changes(crosswalk, committed)

        # rows store country ids, so a countries rebuilt upstream (passed in) forces a rebuild even when subdivision sources are unchanged
        if not has_update and not decisions_changed and not crosswalk_changed and countries is None:
            ingest_log.writeline("No updates for subdivisions, their resolution decisions, the Wikidata crosswalk or countries.")
            # same mappings, so committing only settles the file's formatting
            commit_crosswalk()
            return None
        record_pending(SUBDIVISIONS_MANIFEST_PATH, DECISIONS_MANIFEST_KEY, decisions)

        # Cache countries by alpha2 code, unless already provided by a prior ingest stage
        if countries is None:
            countries = load_countries()

        # GeoNames' subdivisions, indexed by country and admin level and by each id and code
        sub_map: SubdivisionMap = map_geonames_subdivisions(countries)

        # Enrich GeoNames subdivisions with alternate names before merging, so the extra name variants are also available to fuzzy matching
        merge_alternate_name_aliases(sub_map)

        # Cache and dedupe iso subs by id
        iso_subs, non_administrative_subs = load_iso_subs(countries, resolution_map)

        # Apply skill-resolved decisions directly, before auto-merge ever sees these iso_subs, so a verified decision can never lose its target to a fresh auto-merge
        remaining_iso_subs = apply_skill_decisions(iso_subs, resolution_map, sub_map)

        # Skill decisions win, but only knowingly: any that disagree with a valid Wikidata mapping they weren't made against go back to the skill
        flag_wikidata_conflicts(crosswalk, resolution_map, sub_map)

        # Apply unambiguous Wikidata crosswalk matches next, a stronger signal than fuzzy string matching, still ahead of auto-merge; one that changes a previous resolution goes to the skill instead
        remaining_iso_subs = apply_wikidata_matches(remaining_iso_subs, resolution_map, sub_map, crosswalk, committed)

        # Non-administrative groupings take their GeoNames twin, if any, once their children have merged and before auto-merge, so a child can't match the twin
        apply_non_administrative(non_administrative_subs, sub_map, resolution_map)

        # Auto-merge whatever's left with fuzzy matching; writes resolutions/orphans directly into resolution_map
        try_merge(remaining_iso_subs, sub_map, resolution_map)

        # Catch an automerge into a grouping's twin that apply_non_administrative() couldn't identify in time
        flag_grouping_twin_merges(non_administrative_subs, sub_map, resolution_map)

        # rebuild cache with complete data, update parents
        sub_map.refresh()

        resolution_map.save(RESOLUTION_MAP_PATH)

        # refuse to dump subdivisions or hand off to cities (which depends on this run's geocode map) until resolved
        exit_if_orphans(resolution_map)

        dump_registry("subdivisions", sub_map.all())
        write_unmerged_doc(sub_map)
        # only now are this run's sources consumed; a run stopped by orphans leaves them pending, so the next run reprocesses them
        commit_manifest(SUBDIVISIONS_MANIFEST_PATH)
        commit_manifest(SHARED_MANIFEST_PATH)
        commit_crosswalk()
        ingest_log.writeline(f"completed: {len(sub_map)} subdivisions")
        return sub_map.to_geocode_map()
    finally:
        ingest_log.dump()
