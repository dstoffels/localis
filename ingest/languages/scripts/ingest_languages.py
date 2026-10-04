# This script builds ISO 639-3's languages as published by iso-codes, with CLDR's English language names as aliases and CLDR's scripts for each language.

from .fetch_languages import fetch_languages_sources
from .load_languages import load_languages
from ingest.shared.models import LanguageModel, ScriptModel
from ingest.scripts.scripts import load_scripts
from ingest.utils import ingest_log, commit_manifest, dump_registry, LANGUAGES_MANIFEST_PATH


def ingest_languages(scripts: dict[str, ScriptModel] | None = None, force: bool = False) -> dict[str, LanguageModel] | None:
    ingest_log.set_stage("LANGUAGES")
    try:
        has_update = fetch_languages_sources(force=force)
        # rows store script ids, so scripts rebuilt upstream (passed in) force a rebuild even when language sources are unchanged
        if not has_update and scripts is None:
            ingest_log.writeline("No updates for languages or scripts.")
            return None
        if scripts is None:
            scripts = load_scripts()
        languages = load_languages(scripts)
        dump_registry("languages", list(languages.values()))
        commit_manifest(LANGUAGES_MANIFEST_PATH)
        ingest_log.writeline(f"completed: {len(languages)} languages")
        return languages
    finally:
        ingest_log.dump()


if __name__ == "__main__":
    ingest_languages(force=True)
