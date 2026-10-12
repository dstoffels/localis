import gzip
from collections import Counter
from pathlib import Path
import pytest
from localis.entities import CountryLanguage, Language, LanguageBase, LanguageScript, ScriptBase
from ingest.utils import change_report


def _language(id: int, script_name: str, secondary: bool) -> Language:
    script = LanguageScript(id=id, name=script_name, alpha4="Latn", secondary=secondary)
    return Language(
        id=id, name="Demo", alpha3="dmo", alpha2=None, bibliographic=None, scope="individual", type="living",
        inverted_name=None, aliases=[], scripts=[script],
    )


def _write_rows(root: Path, name: str, rows: list[str]) -> Path:
    path = root / name / f"{name}.tsv.gz"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress("".join(f"{row}\n" for row in rows).encode("utf-8")))
    return path


def _added() -> change_report.Changes:
    return change_report.Changes(1, 2, ["`k` K"], [], [], 0, Counter())


class TestChangeReport:
    """CHANGE REPORT"""

    def test_compare(self):
        """should count both builds, list records added and removed by key and renamed with both names, and count records changed, in all and per field"""
        shipped = [("a", "A", {"x": 1}), ("b", "B", {"x": 1}), ("c", "C", {"x": 1, "y": 2}), ("e", "E", {"name": "E", "y": 2})]
        staged = [("a", "A", {"x": 1}), ("c", "C", {"x": 1, "y": 3}), ("d", "D", {"x": 1}), ("e", "F", {"name": "F", "y": 3})]

        result = change_report._compare(shipped, staged)

        assert result == change_report.Changes(4, 4, ["`d` D"], ["`b` B"], ["`e` E → F"], 2, Counter({"y": 2, "name": 1}))

    def test_unchanged_run_omitted(self):
        """should leave a registry that didn't change out of a run's table, and write no table for a run that changed none"""
        unchanged = change_report.Changes(1, 1, [], [], [], 0, Counter())
        run = change_report._counts_section("today", [("same", unchanged), ("other", _added())])

        assert not [line for line in run if line.startswith("| Same ")]
        assert change_report._counts_section("today", [("same", unchanged)]) == []

    def test_lists_linked_from_table(self):
        """should link a run's table to its section of the data changelog only when it renamed, added or removed a record"""
        when = "2026-01-01 12:34 UTC"
        changed_only = change_report.Changes(1, 1, [], [], [], 1, Counter({"x": 1}))
        lists = change_report._records_section(when, [("demo", _added())])
        anchor = f"{change_report.DATA_CHANGELOG_URL}#2026-01-01-1234-utc"

        assert lists[0] == f"## {when}"
        assert any(anchor in line for line in change_report._counts_section(when, [("demo", _added())]))
        assert change_report._records_section(when, [("demo", changed_only)]) == []
        assert not any(anchor in line for line in change_report._counts_section(when, [("demo", changed_only)]))

    def test_prepend_records_newest_first(self):
        """should put each run's lists above the earlier runs', below the data changelog's header"""
        data_changelog = change_report.DATA_CHANGELOG_HEADER
        for when in ("first", "second"):
            data_changelog = change_report._prepend_records(data_changelog, change_report._records_section(when, [("demo", _added())]))
        lines = data_changelog.split("\n")

        assert lines[0] == "# Data changelog"
        assert lines.index("## second") < lines.index("## first")
        assert "\n\n\n" not in data_changelog

    def test_insert_counts_newest_first(self):
        """should add the data subsection last under [Unreleased], then insert each run first in it, leaving the hand-written subsections and releases in place"""
        changelog = "# Changelog\n\n## [Unreleased]\n\n### Fixed\n\n- a fix\n\n## [1.0.0] - 2026-01-01\n"
        for when in ("first", "second"):
            changelog = change_report._insert_counts(changelog, change_report._counts_section(when, [("demo", _added())]))
        lines = changelog.split("\n")

        assert lines.index("### Fixed") < lines.index(change_report.DATA) < lines.index("#### second") < lines.index("#### first") < lines.index("## [1.0.0] - 2026-01-01")
        assert "\n\n\n" not in changelog

    def test_insert_counts_restores_unreleased(self):
        """should add [Unreleased] above the releases when the changelog has none"""
        run = change_report._counts_section("today", [("demo", _added())])
        lines = change_report._insert_counts("# Changelog\n\n## [1.0.0] - 2026-01-01\n", run).split("\n")

        assert lines.index(change_report.UNRELEASED) < lines.index(change_report.DATA) < lines.index("#### today") < lines.index("## [1.0.0] - 2026-01-01")

    def test_nested_base_as_key(self):
        """should reduce a nested record in its base form to its key"""
        assert change_report._nested(LanguageBase(id=1, name="Demo", alpha3="dmo", alpha2=None)) == "dmo"

    def test_nested_keeps_relationship_fields(self):
        """should keep the fields a nested record carries beyond its base form, its own nested records as keys"""
        language = CountryLanguage(
            id=1, name="Demo", alpha3="dmo", alpha2=None, status="official", population_percent=50.0,
            script=ScriptBase(id=1, name="Latin", alpha4="Latn"),
        )

        assert change_report._nested(language) == ("dmo", {"status": "official", "population_percent": 50.0, "script": "Latn"})

    def test_comparable_ignores_nested_record_changes(self):
        """should compare a record without its id or the names of its nested records, but with their relationship fields"""
        before = change_report._comparable(_language(1, "Latin", secondary=False))

        assert change_report._comparable(_language(2, "Roman", secondary=False)) == before
        assert change_report._comparable(_language(1, "Latin", secondary=True)) != before

    def test_realign_shipped(self, tmp_path: Path):
        """should realign shipped rows to this build's columns by name, added ones empty and removed ones dropped, leave matching registries in place, and fall back to appended columns where none were recorded"""
        shipped, scratch = tmp_path / "shipped", tmp_path / "scratch"
        _write_rows(shipped, "currencies", ["1\t2\t3"])
        _write_rows(shipped, "scripts", ["1\t2"])
        _write_rows(shipped, "languages", ["1\t2"])

        realigned = change_report._realign_shipped(
            shipped,
            {"currencies": ["a", "b", "c"], "scripts": ["a", "b"]},
            {"currencies": ["a", "c", "d"], "scripts": ["a", "b"], "languages": ["a", "b", "c"]},
            scratch,
        )

        assert realigned == {"currencies": scratch, "languages": scratch}
        assert gzip.decompress((scratch / "currencies" / "currencies.tsv.gz").read_bytes()).decode("utf-8") == "1\t3\t\n"
        assert gzip.decompress((scratch / "languages" / "languages.tsv.gz").read_bytes()).decode("utf-8") == "1\t2\t\n"
        assert not (scratch / "scripts").exists()
        with pytest.raises(ValueError):
            change_report._realign_shipped(shipped, {}, {"currencies": ["a", "b"]}, tmp_path / "scratch2")
