from dataclasses import asdict, fields, is_dataclass
from pathlib import Path
from typing import Any, Iterator, TypeVar, cast
from localis.entities import Entity
from localis.registries import (
    Registry,
    MacroregionRegistry,
    CurrencyRegistry,
    ScriptRegistry,
    LanguageRegistry,
    CountryRegistry,
    SubdivisionRegistry,
    CityRegistry,
)
from .paths import DATA_PATH, STAGED_DATA_PATH, Stage
from .staging import stage_text

REPORT_NAME = "change_report.md"

R = TypeVar("R", bound=Registry)


def _rooted(cls: type[R], root: Path) -> type[R]:
    """cls reading its data from under root instead of the packaged data."""
    return cast(type[R], type(cls.__name__, (cls,), {"_data_path": property(lambda self: root / self.REGISTRY_NAME)}))


def _registries(root: Path) -> list[Registry]:
    """A separate set of registries over the build under root, so localis's own singletons are left alone."""
    macroregions = _rooted(MacroregionRegistry, root)()
    currencies = _rooted(CurrencyRegistry, root)()
    scripts = _rooted(ScriptRegistry, root)()
    languages = _rooted(LanguageRegistry, root)(scripts=scripts)
    countries = _rooted(CountryRegistry, root)(macroregions=macroregions, currencies=currencies, scripts=scripts, languages=languages)
    subdivisions = _rooted(SubdivisionRegistry, root)(countries=countries)
    cities = _rooted(CityRegistry, root)(countries=countries, subdivisions=subdivisions)
    return [macroregions, currencies, scripts, languages, countries, subdivisions, cities]


def _value(value: Any) -> Any:
    if isinstance(value, Entity):
        return _nested(value)
    if isinstance(value, tuple):
        return tuple(_value(v) for v in value)
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


def _nested(entity: Entity) -> Any:
    """A nested record as its key, which a change to the record itself doesn't touch, plus any facts about the relationship it carries beyond its base form (a CountryLanguage's status)."""
    # the class directly under Entity, the form every nested record of the type shares
    base = next(c for c in type(entity).__mro__ if Entity in c.__bases__)
    base_fields = {f.name for f in fields(base)}
    extra = {f.name: _value(getattr(entity, f.name)) for f in fields(entity) if f.name not in base_fields}
    return (entity.key, extra) if extra else entity.key


def _comparable(entity: Entity) -> dict[str, Any]:
    """The record's fields without its id, which every build renumbers."""
    return {f.name: _value(getattr(entity, f.name)) for f in fields(entity) if f.name != "id"}


def _records(registry: Registry) -> Iterator[tuple[Any, str, dict[str, Any]]]:
    """Each record's key, name and comparable fields, built one at a time."""
    try:
        views = registry._cache.values()
    except FileNotFoundError:
        return
    for view in views:
        entity = view.to_entity()
        yield entity.key, entity.name, _comparable(entity)


def _compare(shipped: Registry, staged: Registry) -> tuple[int, int, list[str], list[str], list[str]]:
    """Each build's record count, and the staged build's records added, removed and changed by key against the shipped one; only the shipped side is held in memory."""
    before = {key: (name, record) for key, name, record in _records(shipped)}
    count_before = len(before)
    added: list[str] = []
    changed: list[str] = []
    count_after = 0
    for key, name, record in _records(staged):
        count_after += 1
        old = before.pop(key, None)
        if old is None:
            added.append(f"`{key}` {name}")
        elif old[1] != record:
            fields_changed = sorted(f for f in record.keys() | old[1].keys() if record.get(f) != old[1].get(f))
            changed.append(f"`{key}` {name}: {', '.join(fields_changed)}")
    removed = [f"`{key}` {name}" for key, (name, _) in before.items()]
    return count_before, count_after, added, removed, changed


def _section(title: str, items: list[str]) -> list[str]:
    return [f"## {title} ({len(items):,})", "", *(f"- {item}" for item in items), ""] if items else []


def write_change_report() -> None:
    """Stages each stage's report of what the staged build changes in its registry against the shipped one, in ingest/<stage>/outputs/: a counts table, which the ingest workflow gathers into the PR's summary, then every record added, removed and changed."""
    for shipped, staged in zip(_registries(DATA_PATH), _registries(STAGED_DATA_PATH)):
        count_before, count_after, added, removed, changed = _compare(shipped, staged)
        name = staged.REGISTRY_NAME
        header = [
            f"# {name.capitalize()} changes",
            "",
            "Records compared by `key` between the shipped data and this build.",
            "",
            "| Records | Added | Removed | Changed |",
            "|---|---|---|---|",
            f"| {count_before:,} → {count_after:,} | {len(added):,} | {len(removed):,} | {len(changed):,} |",
            "",
        ]
        sections = [*_section("Added", added), *_section("Removed", removed), *_section("Changed", changed)]
        # a registry is built by the stage of the same name
        stage_text(Stage(name).outputs / REPORT_NAME, "\n".join([*header, *sections]).rstrip() + "\n")
