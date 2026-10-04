import json
from ingest.shared.models import CountryModel, CountryLanguageModel, LanguageModel, LanguageStatus, ScriptModel
from ingest.shared.scripts.fetch_shared import CLDR_TERRITORY_INFO_PATH
from ingest.languages.scripts import language_codes
from ingest.utils import ingest_log

# CLDR's official statuses, named as localis ships them; a language with no status isn't listed
STATUSES: dict[str, LanguageStatus] = {"official": "official", "official_regional": "regional", "de_facto_official": "de_facto"}


def _parse_tag(tag: str) -> tuple[str, str | None]:
    """A territoryInfo language tag's language code and script code ("sr_Latn" to sr and Latn, "de" to de and None); any other shape fails the ingest rather than being guessed at."""
    parts = tag.split("_")
    if len(parts) == 1:
        return parts[0], None
    if len(parts) == 2 and len(parts[1]) == 4 and parts[1].istitle():
        return parts[0], parts[1]
    raise ValueError(f"CLDR territoryInfo tag {tag!r} isn't a language code with an optional script")


def place_languages(countries: dict[str, CountryModel], languages: dict[str, LanguageModel], scripts: dict[str, ScriptModel]) -> None:
    """Sets each current country's languages from CLDR's territoryInfo: one entry per tag with an official status, keeping the tag's script, ordered by population share; historic countries get none, since CLDR keys territories by alpha2 and ISO reused historic ones."""
    ingest_log.writeline("Placing countries' languages...")
    territories: dict[str, dict] = json.loads(CLDR_TERRITORY_INFO_PATH.read_text(encoding="utf-8"))["supplemental"]["territoryInfo"]
    by_code = language_codes(languages)

    without: list[str] = []
    for country in countries.values():
        if country.historic:
            continue
        for tag, info in territories.get(country.alpha2, {}).get("languagePopulation", {}).items():
            raw_status = info.get("_officialStatus")
            if raw_status is None:
                continue
            status = STATUSES.get(raw_status)
            if status is None:
                raise ValueError(f"CLDR gives {country.alpha2} language {tag} an unknown official status {raw_status!r}")
            code, script_code = _parse_tag(tag)
            language = by_code.get(code)
            if language is None:
                ingest_log.writeline(f"CLDR gives {country.alpha2} ({country.name}) {status} language {tag}, which isn't in ISO 639-3; skipped", level="WARN")
                continue
            script = scripts.get(script_code) if script_code else None
            if script_code and script is None:
                ingest_log.writeline(f"CLDR gives {country.alpha2} ({country.name}) language {tag}, whose script isn't in ISO 15924; skipped", level="WARN")
                continue
            percent = info.get("_populationPercent")
            country.languages.append(
                CountryLanguageModel(language=language, status=status, population_percent=float(percent) if percent else None, script=script)
            )
        # stable, so equal shares keep CLDR's order
        country.languages.sort(key=lambda l: -(l.population_percent or 0.0))
        if not country.languages:
            without.append(country.alpha2)

    entries = sum(len(c.languages) for c in countries.values())
    ingest_log.writeline(f"{entries} country languages; current countries without one: {', '.join(without) or 'none'}")
