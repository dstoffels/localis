# This stage builds ISO 639-3's languages as published by iso-codes, with CLDR's English language names as aliases and CLDR's scripts for each language.

from .fetch_languages import fetch_languages_sources
from .load_languages import load_languages
from ingest.shared.models import LanguageModel, ScriptModel
from ingest.utils import LANGUAGES, ingest_log, dump_registry


def ingest_languages(scripts: dict[str, ScriptModel]) -> dict[str, LanguageModel]:
    with ingest_log.stage(LANGUAGES):
        fetch_languages_sources()
        languages = load_languages(scripts)
        dump_registry("languages", list(languages.values()))
        ingest_log.writeline(f"completed: {len(languages)} languages")
        return languages
