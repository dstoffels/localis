import json
from ingest.shared.models import ScriptModel
from ingest.utils import ingest_log
from ingest.utils.strings import dedupe
from .fetch_scripts import ISO_SCRIPTS_PATH, CLDR_SCRIPT_NAMES_PATH


def load_scripts() -> dict[str, ScriptModel]:
    """ISO 15924's script codes as published, keyed by alpha4, with CLDR's English names for each code as aliases."""
    ingest_log.writeline("Loading ISO 15924 scripts...")
    entries: list[dict[str, str]] = json.loads(ISO_SCRIPTS_PATH.read_text(encoding="utf-8"))["15924"]
    scripts: dict[str, ScriptModel] = {}
    for entry in entries:
        alpha4, numeric = entry["alpha_4"], entry.get("numeric")
        if alpha4 in scripts:
            raise ValueError(f"iso-codes' iso_15924.json lists {alpha4} twice ({scripts[alpha4].name!r} and {entry['name']!r}), and a code must name one script; check the file at the iso-codes commit in scripts.manifest.json and decide in load_scripts() which entry to keep")
        scripts[alpha4] = ScriptModel(name=entry["name"], alpha4=alpha4, numeric=int(numeric) if numeric else None)

    # keys are a code ("Hans") or an alternate form of one ("Hans-alt-stand-alone"); the code is the part before the first hyphen
    names: dict[str, str] = json.loads(CLDR_SCRIPT_NAMES_PATH.read_text(encoding="utf-8"))["main"]["en"]["localeDisplayNames"]["scripts"]
    unresolved: set[str] = set()
    for key, name in names.items():
        script = scripts.get(key.split("-")[0])
        if script is None:
            unresolved.add(key.split("-")[0])
            continue
        script.aliases.append(name)
    for script in scripts.values():
        script.aliases = dedupe(script.aliases, exclude=(script.name,))

    if unresolved:
        # such as Qaag, CLDR's private-use code for Zawgyi
        ingest_log.writeline(f"CLDR names scripts not in ISO 15924, skipped: {', '.join(sorted(unresolved))}")
    ingest_log.writeline(f"{len(scripts)} scripts, {sum(1 for s in scripts.values() if s.aliases)} with CLDR aliases")
    return scripts
