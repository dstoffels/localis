import re
from collections import Counter
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, TypeVar, cast
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
from .paths import REPO_PATH, DATA_PATH, STAGED_DATA_PATH
from .staging import stage_text

CHANGELOG_PATH = REPO_PATH / "CHANGELOG.md"
UNRELEASED = "## [Unreleased]"
DATA = "### Data"
DATA_CHANGELOG_PATH = REPO_PATH / "DATA_CHANGELOG.md"
# absolute, so the links work in the GitHub release notes the CHANGELOG becomes
DATA_CHANGELOG_URL = "https://github.com/dstoffels/localis/blob/main/DATA_CHANGELOG.md"
DATA_CHANGELOG_HEADER = """# Data changelog

Every record an ingest run renamed, added or removed, by `key`, newest first. Each run's counts, with its other changed records counted per field, are in [CHANGELOG.md](https://github.com/dstoffels/localis/blob/main/CHANGELOG.md) under the release that shipped it.
"""

R = TypeVar("R", bound=Registry)


def _rooted(cls: type[R], root: Path) -> type[R]:
    """cls reading its data from under root instead of the packaged data."""
    return cast(type[R], type(cls.__name__, (cls,), {"_data_path": property(lambda self: root / self.REGISTRY_NAME)}))


def _registries(root: Path) -> list[Registry]:
    """Registries over the build under root, apart from localis's own singletons."""
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
    if isinstance(value, (list, tuple)):
        return tuple(_value(v) for v in value)
    if is_dataclass(value) and not isinstance(value, type):
        return asdict(value)
    return value


def _nested(entity: Entity) -> Any:
    """A nested record as its key, plus any relationship fields beyond its base form (a CountryLanguage's status)."""
    # the class directly under Entity
    base = next(c for c in type(entity).__mro__ if Entity in c.__bases__)
    base_fields = {f.name for f in fields(base)}
    extra = {f.name: _value(getattr(entity, f.name)) for f in fields(entity) if f.name not in base_fields}
    return (entity.key, extra) if extra else entity.key


def _comparable(entity: Entity) -> dict[str, Any]:
    """The record's fields without its id, which every build renumbers."""
    return {f.name: _value(getattr(entity, f.name)) for f in fields(entity) if f.name != "id"}


# a record's key, name and comparable fields
Record = tuple[Any, str, dict[str, Any]]


def _records(registry: Registry) -> Iterator[Record]:
    """Each record's key, name and comparable fields; none for a registry new in this build."""
    try:
        views = registry._cache.values()
    except FileNotFoundError:
        # a registry that shipped must be read, or every record of it would count as added
        if registry._data_path.exists():
            raise
        return
    for view in views:
        entity = view.to_entity()
        yield entity.key, entity.name, _comparable(entity)


@dataclass
class Changes:
    """A registry's changes from one build to the next: its records added, removed and renamed by key, and how many it changed, in all and per field."""

    count_before: int
    count_after: int
    added: list[str]
    removed: list[str]
    renamed: list[str]
    changed: int
    changed_fields: Counter[str]

    def __bool__(self) -> bool:
        return bool(self.added or self.removed or self.changed)


def _compare(shipped: Iterable[Record], staged: Iterable[Record]) -> Changes:
    """The staged build's changes to the shipped one, compared by key."""
    before = {key: (name, record) for key, name, record in shipped}
    count_before = len(before)
    added: list[str] = []
    renamed: list[str] = []
    changed = 0
    changed_fields: Counter[str] = Counter()
    count_after = 0
    for key, name, record in staged:
        count_after += 1
        old = before.pop(key, None)
        if old is None:
            added.append(f"`{key}` {name}")
        elif old[1] != record:
            changed += 1
            changed_fields.update(f for f in record.keys() | old[1].keys() if record.get(f) != old[1].get(f))
            if old[0] != name:
                renamed.append(f"`{key}` {old[0]} → {name}")
    removed = [f"`{key}` {name}" for key, (name, _) in before.items()]
    return Changes(count_before, count_after, added, removed, renamed, changed, changed_fields)


def _listed(title: str, items: list[str]) -> list[str]:
    return [f"**{title} ({len(items):,})**", "", *(f"- {item}" for item in items), ""] if items else []


def _anchor(heading: str) -> str:
    """GitHub's id for a heading."""
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def _run_lists(when: str, datasets: list[tuple[str, Changes]]) -> list[str]:
    """A run's section of the data changelog: each registry's records renamed, with both names, added and removed; none if it has none."""
    lines: list[str] = []
    for name, c in datasets:
        listed = [*_listed("Renamed", c.renamed), *_listed("Added", c.added), *_listed("Removed", c.removed)]
        if listed:
            lines += [f"### {name.capitalize()}", "", *listed]
    while lines and not lines[-1]:
        lines.pop()
    return [f"## {when}", "", *lines] if lines else []


def _run_table(when: str, datasets: list[tuple[str, Changes]]) -> list[str]:
    """A run's section of the changelog's data changes: a table of each registry it changed, linked to its records in the data changelog if it listed any; none if it changed no registry."""
    changed = [(name, changes) for name, changes in datasets if changes]
    if not changed:
        return []
    lines = [f"#### {when}", "", "| Dataset | Records | Added | Removed | Changed | Changed fields |", "|---|---|---|---|---|---|"]
    for name, c in changed:
        by_count = ", ".join(f"`{field}` ({count:,})" for field, count in sorted(c.changed_fields.items(), key=lambda item: (-item[1], item[0])))
        lines.append(f"| {name.capitalize()} | {c.count_before:,} → {c.count_after:,} | {len(c.added):,} | {len(c.removed):,} | {c.changed:,} | {by_count} |")
    if any(c.renamed or c.added or c.removed for _, c in changed):
        lines += ["", f"[Records renamed, added and removed]({DATA_CHANGELOG_URL}#{_anchor(when)})"]
    return lines


def _insert_run(changelog: str, run: list[str]) -> str:
    """The changelog with the run's section first under [Unreleased]'s data changes, a subsection added last if missing, as is [Unreleased] above the releases."""
    lines = changelog.rstrip("\n").split("\n")
    if UNRELEASED not in lines:
        first_release = next((i for i, line in enumerate(lines) if line.startswith("## ")), len(lines))
        lines[first_release:first_release] = [UNRELEASED, ""]
    start = lines.index(UNRELEASED) + 1
    end = next((i for i in range(start, len(lines)) if lines[i].startswith("## ")), len(lines))
    if DATA in lines[start:end]:
        at = lines.index(DATA, start) + 1
        lines[at:at] = ["", *run]
    else:
        # last, after the hand-written subsections
        while end > start and not lines[end - 1]:
            end -= 1
        lines[end:end] = ["", DATA, "", *run]
    return "\n".join(lines) + "\n"


def _prepend_run(data_changelog: str, run: list[str]) -> str:
    """The data changelog with the run's section above the earlier runs."""
    lines = data_changelog.rstrip("\n").split("\n")
    at = next((i for i, line in enumerate(lines) if line.startswith("## ")), None)
    if at is None:
        lines += ["", *run]
    else:
        lines[at:at] = [*run, ""]
    return "\n".join(lines) + "\n"


def _compare_builds(shipped_root: Path, staged_root: Path) -> list[tuple[str, Changes]]:
    """Each registry's changes from the build under shipped_root to the one under staged_root."""
    return [(staged.REGISTRY_NAME, _compare(_records(shipped), _records(staged))) for shipped, staged in zip(_registries(shipped_root), _registries(staged_root))]


def write_change_report() -> None:
    """Stages this run's table first under the changelog's [Unreleased] data changes and its records renamed, added and removed first in the data changelog; a run that changed no record writes neither."""
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    datasets = _compare_builds(DATA_PATH, STAGED_DATA_PATH)
    table = _run_table(when, datasets)
    if not table:
        return
    stage_text(CHANGELOG_PATH, _insert_run(CHANGELOG_PATH.read_text(encoding="utf-8"), table))
    if lists := _run_lists(when, datasets):
        data_changelog = DATA_CHANGELOG_PATH.read_text(encoding="utf-8") if DATA_CHANGELOG_PATH.exists() else DATA_CHANGELOG_HEADER
        stage_text(DATA_CHANGELOG_PATH, _prepend_run(data_changelog, lists))
