import re
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, fields, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, TypeVar, cast
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
from localis.utils.data import open_data
from .index import gzip_bytes
from .logger import pipeline_log
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


def _registries(root: Path, realigned: Mapping[str, Path] | None = None) -> list[Registry]:
    """Registries over the build under root, apart from localis's singletons; one named in realigned reads from its root there."""
    roots = realigned or {}

    def at(cls: type[R]) -> type[R]:
        return _rooted(cls, roots.get(cls.REGISTRY_NAME, root))

    macroregions = at(MacroregionRegistry)()
    currencies = at(CurrencyRegistry)()
    scripts = at(ScriptRegistry)()
    languages = at(LanguageRegistry)(scripts=scripts)
    countries = at(CountryRegistry)(macroregions=macroregions, currencies=currencies, scripts=scripts, languages=languages)
    subdivisions = at(SubdivisionRegistry)(countries=countries)
    cities = at(CityRegistry)(countries=countries, subdivisions=subdivisions)
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
    """Yields nothing for a registry new in this build."""
    try:
        views = registry._cache.values()
    except FileNotFoundError:
        # a shipped registry must be readable, or every record would count as added
        if registry._data_path.exists():
            raise
        return
    for view in views:
        entity = view.to_entity()
        yield entity.key, entity.name, _comparable(entity)


@dataclass
class Changes:
    """A registry's changes from one build to the next."""

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
    """Matches records by key."""
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


def _github_anchor(heading: str) -> str:
    return re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")


def _records_section(when: str, datasets: list[tuple[str, Changes]]) -> list[str]:
    """DATA_CHANGELOG.md's section for a run; empty if it renamed, added and removed nothing."""
    lines: list[str] = []
    for name, c in datasets:
        listed = [*_listed("Renamed", c.renamed), *_listed("Added", c.added), *_listed("Removed", c.removed)]
        if listed:
            lines += [f"### {name.capitalize()}", "", *listed]
    while lines and not lines[-1]:
        lines.pop()
    return [f"## {when}", "", *lines] if lines else []


def _counts_section(when: str, datasets: list[tuple[str, Changes]]) -> list[str]:
    """CHANGELOG.md's section for a run; empty if it changed nothing."""
    changed = [(name, changes) for name, changes in datasets if changes]
    if not changed:
        return []
    lines = [f"#### {when}", "", "| Dataset | Records | Added | Removed | Changed | Changed fields |", "|---|---|---|---|---|---|"]
    for name, c in changed:
        by_count = ", ".join(f"`{field}` ({count:,})" for field, count in sorted(c.changed_fields.items(), key=lambda item: (-item[1], item[0])))
        lines.append(f"| {name.capitalize()} | {c.count_before:,} → {c.count_after:,} | {len(c.added):,} | {len(c.removed):,} | {c.changed:,} | {by_count} |")
    if any(c.renamed or c.added or c.removed for _, c in changed):
        lines += ["", f"[Records renamed, added and removed]({DATA_CHANGELOG_URL}#{_github_anchor(when)})"]
    return lines


def _insert_counts(changelog: str, run: list[str]) -> str:
    """Inserts the section first under [Unreleased]'s ### Data, adding either heading if missing."""
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


def _prepend_records(data_changelog: str, run: list[str]) -> str:
    lines = data_changelog.rstrip("\n").split("\n")
    at = next((i for i, line in enumerate(lines) if line.startswith("## ")), None)
    if at is None:
        lines += ["", *run]
    else:
        lines[at:at] = [*run, ""]
    return "\n".join(lines) + "\n"


def _first_row(path: Path) -> list[str]:
    with open_data(path) as f:
        return f.readline().rstrip("\r\n").split("\t")


def _realign_shipped(shipped_root: Path, staged_root: Path, scratch: Path) -> dict[str, Path]:
    """The scratch root of each registry whose shipped rows needed realigning to this build's header: added columns empty, removed ones dropped."""
    realigned: dict[str, Path] = {}
    for directory in sorted(staged_root.iterdir()):
        name = directory.name
        staged, source = directory / f"{name}.tsv.gz", shipped_root / name / f"{name}.tsv.gz"
        if not (staged.exists() and source.exists()):
            continue
        columns, old = _first_row(staged), _first_row(source)
        if old == columns:
            continue
        # every header starts with name
        if old[0] != "name":
            raise ValueError(f"{source} has no header to read its columns by")
        positions = [old.index(column) if column in old else None for column in columns]
        target = scratch / name / source.name
        target.parent.mkdir(parents=True)
        with open_data(source) as f:
            f.readline()
            rows = (line.rstrip("\r\n").split("\t") for line in f)
            text = "".join("\t".join(cells[i] if i is not None else "" for i in positions) + "\n" for cells in rows)
        target.write_bytes(gzip_bytes(("\t".join(columns) + "\n" + text).encode("utf-8")))
        realigned[name] = scratch
        added, removed = [c for c in columns if c not in old], [c for c in old if c not in columns]
        pipeline_log.writeline(f"{name}: compared with the shipped rows realigned to this build's columns (added: {', '.join(added) or 'none'}; removed: {', '.join(removed) or 'none'})")
    return realigned


def _compare_builds(shipped_root: Path, staged_root: Path) -> list[tuple[str, Changes]]:
    with tempfile.TemporaryDirectory() as scratch:
        realigned = _realign_shipped(shipped_root, staged_root, Path(scratch))
        return [(staged.REGISTRY_NAME, _compare(_records(shipped), _records(staged))) for shipped, staged in zip(_registries(shipped_root, realigned), _registries(staged_root))]


def write_data_changes() -> None:
    """Stages this run's sections of CHANGELOG.md and DATA_CHANGELOG.md; a run that changed no record writes neither."""
    when = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    datasets = _compare_builds(DATA_PATH, STAGED_DATA_PATH)
    table = _counts_section(when, datasets)
    if not table:
        return
    stage_text(CHANGELOG_PATH, _insert_counts(CHANGELOG_PATH.read_text(encoding="utf-8"), table))
    if lists := _records_section(when, datasets):
        data_changelog = DATA_CHANGELOG_PATH.read_text(encoding="utf-8") if DATA_CHANGELOG_PATH.exists() else DATA_CHANGELOG_HEADER
        stage_text(DATA_CHANGELOG_PATH, _prepend_records(data_changelog, lists))
