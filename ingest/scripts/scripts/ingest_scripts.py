# This script builds ISO 15924's script codes as published by iso-codes, with CLDR's English script names as aliases.

from .fetch_scripts import fetch_scripts_sources
from .load_scripts import load_scripts
from ingest.shared.models import ScriptModel
from ingest.utils import ingest_log, commit_manifest, dump_registry, SCRIPTS_MANIFEST_PATH


def ingest_scripts(force: bool = False) -> dict[str, ScriptModel] | None:
    ingest_log.set_stage("SCRIPTS")
    try:
        has_update = fetch_scripts_sources(force=force)
        if not has_update:
            ingest_log.writeline("No updates for scripts.")
            return None
        scripts = load_scripts()
        dump_registry("scripts", list(scripts.values()))
        commit_manifest(SCRIPTS_MANIFEST_PATH)
        ingest_log.writeline(f"completed: {len(scripts)} scripts")
        return scripts
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_scripts(force=True)
