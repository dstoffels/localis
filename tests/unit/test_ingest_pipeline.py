import hashlib
import io
import json
import zipfile
from pathlib import Path
import pytest
from localis.entities import CountryLanguage, Language, LanguageBase, LanguageScript, ScriptBase
from ingest.utils import change_report, download, logger, paths, staging
from ingest.utils.logger import ORPHANS_EXIT_CODE, IngestLog, PipelineLog


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repo under tmp_path, with staging and the shipped data pointed into it."""
    staging_path = tmp_path / "ingest" / "staging"
    for name, value in {
        "REPO_PATH": tmp_path,
        "DATA_PATH": tmp_path / "data",
        "STAGING_PATH": staging_path,
        "STAGED_DATA_PATH": staging_path / "data",
        "STAGED_FILES_PATH": staging_path / "files",
        "FETCHED_PATH": staging_path / "fetched",
        "COMPLETE_MARKER": staging_path / "COMPLETE",
    }.items():
        monkeypatch.setattr(staging, name, value)
    monkeypatch.setattr(paths, "BASE_PATH", tmp_path / "ingest")
    monkeypatch.setattr(logger, "PIPELINE_LOG_PATH", tmp_path / "ingest" / "pipeline.log")
    return tmp_path


class Source:
    """A remote source fetch() reads through stubbed HEAD and download requests."""

    URL = "https://example.org/source"

    def __init__(self, monkeypatch: pytest.MonkeyPatch, content: bytes, etag: str) -> None:
        self.content = content
        self.etag = etag
        self.downloads = 0
        monkeypatch.setattr(download, "_etag", lambda url: self.etag)
        monkeypatch.setattr(download, "_download", self._download)

    def _download(self, url: str, dest: Path) -> str:
        self.downloads += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(self.content)
        return self.etag

    def entry(self) -> dict:
        return {"url": self.URL, "etag": self.etag, "sha256": _sha256(self.content)}


@pytest.fixture
def inputs(repo: Path) -> Path:
    return repo / "ingest" / "demo" / "inputs"


@pytest.fixture
def manifest(inputs: Path) -> Path:
    return inputs / "demo.manifest.json"


class TestFetch:
    """FETCH"""

    def test_downloads_missing_source(self, monkeypatch, inputs, manifest):
        """should download a source missing locally and stage its url, ETag and SHA-256, leaving the committed manifest alone"""
        source = Source(monkeypatch, b"v1", '"1"')

        assert download.fetch(Source.URL, inputs / "source.txt", manifest)
        assert (inputs / "source.txt").read_bytes() == b"v1"
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}
        assert not manifest.exists()

    def test_skips_current_source(self, monkeypatch, inputs, manifest):
        """should not download a source whose local file matches the committed manifest's ETag and SHA-256"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        _write_json(manifest, {"source.txt": source.entry()})

        assert not download.fetch(Source.URL, inputs / "source.txt", manifest)
        assert source.downloads == 0
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_changed_etag(self, monkeypatch, inputs, manifest):
        """should download a source whose ETag differs from its record"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        _write_json(manifest, {"source.txt": source.entry()})
        source.content, source.etag = b"v2", '"2"'

        assert download.fetch(Source.URL, inputs / "source.txt", manifest)
        assert (inputs / "source.txt").read_bytes() == b"v2"
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_altered_local_file(self, monkeypatch, inputs, manifest):
        """should download a source whose local file no longer matches its recorded SHA-256, even under the same ETag"""
        source = Source(monkeypatch, b"v1", '"1"')
        _write_json(manifest, {"source.txt": source.entry()})
        (inputs / "source.txt").write_bytes(b"edited")

        assert download.fetch(Source.URL, inputs / "source.txt", manifest)
        assert (inputs / "source.txt").read_bytes() == b"v1"

    def test_rerun_after_failed_run(self, monkeypatch, inputs, manifest):
        """should not download again on a rerun what a run that never promoted already downloaded"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        _write_json(manifest, {"source.txt": source.entry()})
        source.content, source.etag = b"v2", '"2"'
        download.fetch(Source.URL, inputs / "source.txt", manifest)

        staging.reset_staging()

        assert not download.fetch(Source.URL, inputs / "source.txt", manifest)
        assert source.downloads == 1

    def test_drops_unused_entries(self, monkeypatch, inputs, manifest):
        """should stage a manifest holding only the sources this run fetched"""
        source = Source(monkeypatch, b"v1", '"1"')
        _write_json(manifest, {"source.txt": source.entry(), "unused.txt": source.entry()})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert _read_json(staging.staged_path(manifest)).keys() == {"source.txt"}

    def test_extracts_zip_member(self, monkeypatch, inputs, manifest):
        """should extract the zip's member, remove the zip and record the member's SHA-256 under the zip's name"""
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("source.txt", b"v1")
        Source(monkeypatch, archive.getvalue(), '"1"')

        download.fetch(Source.URL, inputs / "source.zip", manifest, extract="source.txt")

        assert (inputs / "source.txt").read_bytes() == b"v1"
        assert not (inputs / "source.zip").exists()
        assert _read_json(staging.staged_path(manifest))["source.zip"]["sha256"] == _sha256(b"v1")


class TestResetStaging:
    """RESET STAGING"""

    def test_merges_staged_manifests(self, repo, manifest):
        """should merge the last run's staged manifests into the fetched record, its entries replacing older ones"""
        _write_json(staging.fetched_path(manifest), {"a.txt": "older", "b.txt": "kept"})
        _write_json(staging.staged_path(manifest), {"a.txt": "newer", "c.txt": "added"})

        staging.reset_staging()

        assert _read_json(staging.fetched_path(manifest)) == {"a.txt": "newer", "b.txt": "kept", "c.txt": "added"}

    def test_clears_last_build(self, repo):
        """should clear the last run's staged data, staged files and completion marker"""
        staging.STAGED_DATA_PATH.joinpath("demo").mkdir(parents=True)
        staging.stage_text(repo / "docs" / "demo.md", "text")
        staging.mark_complete()

        staging.reset_staging()

        assert list(staging.STAGED_DATA_PATH.iterdir()) == []
        assert not staging.STAGED_FILES_PATH.exists()
        assert not staging.is_complete()


class TestPromote:
    """PROMOTE"""

    @staticmethod
    def _stage_build(repo: Path) -> None:
        for registry, file in (("demo", "old.tsv"), ("other", "other.tsv")):
            (staging.DATA_PATH / registry).mkdir(parents=True)
            (staging.DATA_PATH / registry / file).write_text("shipped")
        (staging.STAGED_DATA_PATH / "demo").mkdir(parents=True)
        (staging.STAGED_DATA_PATH / "demo" / "new.tsv").write_text("staged")
        staging.stage_text(repo / "docs" / "demo.md", "staged")

    def test_refuses_incomplete_build(self, repo):
        """should promote nothing from a build no run marked complete"""
        self._stage_build(repo)

        with pytest.raises(RuntimeError):
            staging.promote()
        assert (staging.DATA_PATH / "demo" / "old.tsv").exists()
        assert not (repo / "docs" / "demo.md").exists()

    def test_moves_build(self, repo, manifest):
        """should replace each staged registry's shipped data, move the staged files to their repo paths and clear staging"""
        self._stage_build(repo)
        _write_json(staging.fetched_path(manifest), {})
        staging.mark_complete()

        staging.promote()

        assert [p.name for p in (staging.DATA_PATH / "demo").iterdir()] == ["new.tsv"]
        assert (staging.DATA_PATH / "other" / "other.tsv").exists()
        assert (repo / "docs" / "demo.md").read_text() == "staged"
        assert not staging.STAGING_PATH.exists()


def _language(id: int, script_name: str, secondary: bool) -> Language:
    script = LanguageScript(id=id, name=script_name, alpha4="Latn", secondary=secondary)
    return Language(
        id=id, name="Demo", alpha3="dmo", alpha2=None, bibliographic=None, scope="individual", type="living",
        inverted_name=None, aliases=(), scripts=(script,),
    )


class TestChangeReport:
    """CHANGE REPORT"""

    def test_compare(self, monkeypatch):
        """should count both builds and list records added, removed and changed by key, with the fields that changed"""
        shipped = [("a", "A", {"x": 1}), ("b", "B", {"x": 1}), ("c", "C", {"x": 1, "y": 2})]
        staged = [("a", "A", {"x": 1}), ("c", "C", {"x": 1, "y": 3}), ("d", "D", {"x": 1})]
        monkeypatch.setattr(change_report, "_records", iter)

        result = change_report._compare(shipped, staged)  # type: ignore[arg-type]

        assert result == (3, 3, ["`d` D"], ["`b` B"], ["`c` C: y"])

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


def _log_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


class TestPipelineLog:
    """PIPELINE LOG"""

    def test_success(self, repo):
        """should log each step, then one line saying the build was promoted"""
        log = PipelineLog()

        with log.run():
            log.step("building demo")

        assert _log_lines(logger.PIPELINE_LOG_PATH) == ["[PIPELINE]", "[INFO] Building demo", "[INFO] Pipeline succeeded: build promoted"]

    def test_orphan_stop(self, repo):
        """should log an orphan stop as a warning against its step, with nothing promoted"""
        log = PipelineLog()

        with pytest.raises(SystemExit), log.run():
            log.step("building subdivisions")
            raise SystemExit(ORPHANS_EXIT_CODE)

        last = _log_lines(logger.PIPELINE_LOG_PATH)[-1]
        assert last.startswith("[WARN] Pipeline stopped while building subdivisions:")
        assert last.endswith("; nothing promoted")

    @pytest.mark.parametrize("promoted, outcome", [(False, "nothing promoted"), (True, "build promoted")])
    def test_failure(self, repo, promoted, outcome):
        """should log a failure as an error against its step, saying whether the build was promoted"""
        log = PipelineLog()

        with pytest.raises(RuntimeError), log.run():
            log.step("checking demo")
            log.promoted = promoted
            raise RuntimeError("boom")

        assert _log_lines(logger.PIPELINE_LOG_PATH)[-1] == f"[ERROR] Pipeline failed while checking demo: RuntimeError: boom; {outcome}"


class TestIngestLog:
    """INGEST LOG"""

    def test_stage_failure(self, repo):
        """should write a failed stage's log with an ERROR line for the exception that stopped it"""
        log = IngestLog()
        stage = paths.Stage("demo")

        with pytest.raises(RuntimeError), log.stage(stage):
            log.writeline("started")
            raise RuntimeError("boom")

        assert _log_lines(stage.log_file) == ["[DEMO]", "[INFO] started", "[ERROR] RuntimeError: boom"]

    def test_lines_outside_stage(self, repo):
        """should keep no line written after a stage ends for any stage's log"""
        log = IngestLog()
        stage = paths.Stage("demo")
        with log.stage(stage):
            log.writeline("inside")

        log.writeline("outside")
        with log.stage(paths.Stage("next")):
            pass

        assert _log_lines(stage.log_file) == ["[DEMO]", "[INFO] inside"]
        assert _log_lines(paths.Stage("next").log_file) == ["[NEXT]"]
