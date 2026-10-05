import json
from ingest.shared.models import LanguageModel, LanguageScriptModel, LanguageScope, LanguageType, ScriptModel
from ingest.utils import ingest_log
from ingest.utils.strings import dedupe
from .fetch_languages import ISO_LANGUAGES_PATH, CLDR_LANGUAGE_NAMES_PATH, CLDR_LANGUAGE_DATA_PATH

# iso-codes' one-letter codes, spelled out
SCOPES: dict[str, LanguageScope] = {"I": "individual", "M": "macrolanguage", "S": "special"}
TYPES: dict[str, LanguageType] = {"L": "living", "E": "extinct", "H": "historical", "C": "constructed", "S": "special"}
SECONDARY_SUFFIX = "-alt-secondary"
# CLDR's "<code>-menu-core" and "<code>-menu-extension" entries ("Kurdish", "Central") are halves of one menu label, not names
MENU_FRAGMENT = "-menu-"


def language_codes(languages: dict[str, LanguageModel]) -> dict[str, LanguageModel]:
    """Each language by the codes CLDR's BCP 47 tags use for it: its alpha2 where it has one, and its alpha3."""
    by_code: dict[str, LanguageModel] = {}
    for language in languages.values():
        by_code[language.alpha3] = language
        if language.alpha2:
            by_code[language.alpha2] = language
    return by_code


def _add_cldr_names(by_code: dict[str, LanguageModel]) -> None:
    """Adds every English name CLDR gives a tag whose language subtag resolves to a record ("en-GB" British English to English, "az-alt-short" Azeri to Azerbaijani) as that record's alias."""
    names: dict[str, str] = json.loads(CLDR_LANGUAGE_NAMES_PATH.read_text(encoding="utf-8"))["main"]["en"]["localeDisplayNames"]["languages"]
    unresolved: set[str] = set()
    for key, name in names.items():
        if MENU_FRAGMENT in key:
            continue
        code = key.split("-")[0]
        language = by_code.get(code)
        if language is None:
            unresolved.add(code)
            continue
        language.aliases.append(name)
    if unresolved:
        ingest_log.writeline(f"CLDR names languages not in ISO 639-3, skipped: {', '.join(sorted(unresolved))}")


def _add_cldr_scripts(by_code: dict[str, LanguageModel], scripts: dict[str, ScriptModel]) -> None:
    """Sets each language's scripts from CLDR's language data: its code's entry lists primary scripts and its "-alt-secondary" entry secondary ones, which TR35 defines as a non-modern language or script; a script listed twice is kept once, and one listed as both raises."""
    data: dict[str, dict[str, list[str]]] = json.loads(CLDR_LANGUAGE_DATA_PATH.read_text(encoding="utf-8"))["supplemental"]["languageData"]
    primary: dict[str, list[LanguageScriptModel]] = {}
    secondary: dict[str, list[LanguageScriptModel]] = {}
    # each language's scripts so far, with whether each is secondary and the CLDR key that listed it, so a repeat is dropped and a contradiction caught
    listed: dict[str, dict[str, tuple[bool, str]]] = {}
    unresolved: set[str] = set()
    for key, entry in data.items():
        code = key.removesuffix(SECONDARY_SUFFIX)
        language = by_code.get(code)
        if language is None:
            unresolved.add(code)
            continue
        is_secondary = key.endswith(SECONDARY_SUFFIX)
        target = secondary if is_secondary else primary
        for script_code in entry.get("_scripts", []):
            script = scripts.get(script_code)
            if script is None:
                ingest_log.writeline(f"CLDR gives {code} script {script_code}, which isn't in ISO 15924; skipped", level="WARN")
                continue
            earlier = listed.setdefault(language.alpha3, {}).get(script_code)
            if earlier is not None:
                if earlier[0] != is_secondary:
                    raise ValueError(f"CLDR's languageData lists {script_code} as both a primary and a secondary script of {language.alpha3} (under {earlier[1]!r} and {key!r}), and a language's script is one or the other; check languageData.json at the cldr-json commit in languages.manifest.json and decide in _add_cldr_scripts() which to keep")
                continue
            listed[language.alpha3][script_code] = (is_secondary, key)
            target.setdefault(language.alpha3, []).append(LanguageScriptModel(script=script, secondary=is_secondary))
    for alpha3 in {*primary, *secondary}:
        by_code[alpha3].scripts = [*primary.get(alpha3, []), *secondary.get(alpha3, [])]
    if unresolved:
        # such as kro, the ISO 639-5 code for the Kru language family
        ingest_log.writeline(f"CLDR gives scripts for codes not in ISO 639-3, skipped: {', '.join(sorted(unresolved))}")


def load_languages(scripts: dict[str, ScriptModel]) -> dict[str, LanguageModel]:
    """ISO 639-3's languages as published, keyed by alpha3, with CLDR's English names as aliases and CLDR's scripts for each."""
    ingest_log.writeline("Loading ISO 639-3 languages...")
    entries: list[dict[str, str]] = json.loads(ISO_LANGUAGES_PATH.read_text(encoding="utf-8"))["639-3"]
    languages: dict[str, LanguageModel] = {}
    for entry in entries:
        alpha3 = entry["alpha_3"]
        scope, type_ = SCOPES.get(entry["scope"]), TYPES.get(entry["type"])
        if scope is None or type_ is None:
            raise ValueError(f"ISO 639-3 {alpha3} has an unknown scope {entry['scope']!r} or type {entry['type']!r}")
        if alpha3 in languages:
            raise ValueError(f"iso-codes' iso_639-3.json lists {alpha3} twice ({languages[alpha3].name!r} and {entry['name']!r}), and a code must name one language; check the file at the iso-codes commit in languages.manifest.json and decide in load_languages() which entry to keep")
        languages[alpha3] = LanguageModel(
            name=entry["name"],
            alpha3=alpha3,
            alpha2=entry.get("alpha_2"),
            bibliographic=entry.get("bibliographic"),
            scope=scope,
            type=type_,
            inverted_name=entry.get("inverted_name"),
            aliases=[entry["common_name"]] if "common_name" in entry else [],
        )

    by_code = language_codes(languages)
    _add_cldr_names(by_code)
    _add_cldr_scripts(by_code, scripts)
    for language in languages.values():
        language.aliases = dedupe(language.aliases, exclude=(language.name, language.inverted_name or ""))

    ingest_log.writeline(
        f"{len(languages)} languages, {sum(1 for l in languages.values() if l.scripts)} with scripts and {sum(1 for l in languages.values() if l.aliases)} with aliases"
    )
    return languages
