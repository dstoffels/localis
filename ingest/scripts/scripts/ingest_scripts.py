# This stage builds ISO 15924's script codes as published by iso-codes, with CLDR's English script names as aliases.

from .fetch_scripts import fetch_scripts_sources
from .load_scripts import load_scripts
from ingest.shared.models import ScriptModel
from ingest.utils import SCRIPTS, ingest_log, dump_registry


def ingest_scripts() -> dict[str, ScriptModel]:
    with ingest_log.stage(SCRIPTS):
        fetch_scripts_sources()
        scripts = load_scripts()
        dump_registry("scripts", list(scripts.values()))
        ingest_log.writeline(f"completed: {len(scripts)} scripts")
        return scripts
