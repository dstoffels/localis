import gzip
import hashlib
import io
import struct
import json
import zipfile
from email.message import Message
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError
import pytest
from localis.entities import CountryLanguage, Language, LanguageBase, LanguageScript, ScriptBase
from ingest.shared.models import CurrencyModel, ScriptModel, SubdivisionModel
from ingest.utils import change_report, download, index, logger, paths, staging
from ingest.utils.committed_query import CONFIRM_QUERIES, CommittedQuery
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

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert (inputs / "source.txt").read_bytes() == b"v1"
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}
        assert not manifest.exists()

    def test_skips_current_source(self, monkeypatch, inputs, manifest):
        """should not download a source whose local file matches the committed manifest's ETag and SHA-256"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        _write_json(manifest, {"source.txt": source.entry()})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert source.downloads == 0
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_changed_etag(self, monkeypatch, inputs, manifest):
        """should download a source whose ETag differs from its record"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        _write_json(manifest, {"source.txt": source.entry()})
        source.content, source.etag = b"v2", '"2"'

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert (inputs / "source.txt").read_bytes() == b"v2"
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_changed_url(self, monkeypatch, inputs, manifest):
        """should download a source whose url differs from its record, even under the same ETag"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        _write_json(manifest, {"source.txt": {**source.entry(), "url": "https://example.org/old"}})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert source.downloads == 1
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_altered_local_file(self, monkeypatch, inputs, manifest):
        """should download a source whose local file no longer matches its recorded SHA-256, even under the same ETag"""
        source = Source(monkeypatch, b"v1", '"1"')
        _write_json(manifest, {"source.txt": source.entry()})
        (inputs / "source.txt").write_bytes(b"edited")

        download.fetch(Source.URL, inputs / "source.txt", manifest)

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
        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert source.downloads == 1

    def test_drops_unused_entries(self, monkeypatch, inputs, manifest):
        """should stage a manifest holding only the sources this run fetched"""
        source = Source(monkeypatch, b"v1", '"1"')
        _write_json(manifest, {"source.txt": source.entry(), "unused.txt": source.entry()})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert _read_json(staging.staged_path(manifest)).keys() == {"source.txt"}

    def test_extracts_zip_member(self, monkeypatch, inputs, manifest):
        """should extract the zip's member, remove the zip and record the member under its own name"""
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("source.txt", b"v1")
        Source(monkeypatch, archive.getvalue(), '"1"')

        download.fetch(Source.URL, inputs / "source.zip", manifest, extract="source.txt")

        assert (inputs / "source.txt").read_bytes() == b"v1"
        assert not (inputs / "source.zip").exists()
        assert _read_json(staging.staged_path(manifest)) == {"source.txt": {"url": Source.URL, "etag": '"1"', "sha256": _sha256(b"v1")}}


class _Response(io.BytesIO):
    """A urlopen response with the body and headers given."""

    def __init__(self, body: bytes, headers: dict[str, str]) -> None:
        super().__init__(body)
        self.headers = headers


class TestDownload:
    """DOWNLOAD"""

    def test_cut_off_body(self, monkeypatch, tmp_path):
        """should raise on a body shorter than its Content-Length, leaving dest unwritten"""
        monkeypatch.setattr(download, "urlopen", lambda request, timeout: _Response(b"v1", {"Content-Length": "10"}))

        with pytest.raises(IncompleteRead):
            download._download(Source.URL, tmp_path / "source.txt")
        assert not (tmp_path / "source.txt").exists()

    def test_complete_body(self, monkeypatch, tmp_path):
        """should write a body matching its Content-Length and return its ETag"""
        monkeypatch.setattr(download, "urlopen", lambda request, timeout: _Response(b"v1", {"Content-Length": "2", "ETag": '"1"'}))

        assert download._download(Source.URL, tmp_path / "source.txt") == '"1"'
        assert (tmp_path / "source.txt").read_bytes() == b"v1"


def _http_error(code: int) -> HTTPError:
    return HTTPError(Source.URL, code, "error", Message(), None)


class TestRetrying:
    """RETRYING"""

    @pytest.fixture(autouse=True)
    def no_sleep(self, monkeypatch):
        monkeypatch.setattr(download.time, "sleep", lambda seconds: None)

    @staticmethod
    def _failing(*failures: Exception):
        """A request raising each failure in turn, then returning "ok"."""
        remaining = list(failures)

        def request() -> str:
            if remaining:
                raise remaining.pop(0)
            return "ok"

        return request

    @pytest.mark.parametrize("failure", [_http_error(503), _http_error(429), TimeoutError(), IncompleteRead(b"", 1), ValueError()])
    def test_retries_transient_failure(self, failure):
        """should retry a 5xx, a 429, a timeout or a cut-off body"""
        assert download._retrying(self._failing(failure), "demo") == "ok"

    def test_raises_client_error(self):
        """should raise a 4xx other than 429 without retrying"""
        with pytest.raises(HTTPError):
            download._retrying(self._failing(_http_error(404)), "demo")

    def test_raises_after_last_attempt(self):
        """should raise the last attempt's failure once every attempt failed"""
        with pytest.raises(TimeoutError):
            download._retrying(self._failing(*[TimeoutError()] * download.REQUEST_ATTEMPTS), "demo")


class TestCommittedQuery:
    """COMMITTED QUERY"""

    @staticmethod
    def _query(repo: Path, committed: dict, *results: dict):
        """A CommittedQuery over a committed result, and a query returning each result in turn."""
        committed_query = CommittedQuery[int](repo / "demo.json", "demo")
        _write_json(committed_query.path, committed)
        remaining = list(results)
        return committed_query, lambda: remaining.pop(0)

    def test_keeps_result_missing_nothing(self, repo):
        """should stage a result missing no committed key without querying again"""
        committed_query, query = self._query(repo, {"a": 1}, {"a": 2, "b": 1})

        assert committed_query.fetch(query) == {"a": 2, "b": 1}
        assert committed_query.latest() == {"a": 2, "b": 1}

    def test_confirms_removal(self, repo):
        """should accept a removal once a repeat is missing the same keys, keeping the repeat even where it differs elsewhere"""
        committed_query, query = self._query(repo, {"a": 1, "b": 1}, {"a": 1}, {"a": 2})

        assert committed_query.fetch(query) == {"a": 2}

    def test_drops_unrepeated_removal(self, repo):
        """should keep a key a repeat returns again"""
        committed_query, query = self._query(repo, {"a": 1, "b": 1}, {"a": 1}, {"a": 1, "b": 1})

        assert committed_query.fetch(query) == {"a": 1, "b": 1}

    def test_raises_when_missing_keys_keep_changing(self, repo):
        """should raise once every query is missing different committed keys"""
        committed = {str(key): 1 for key in range(CONFIRM_QUERIES)}
        results = [{key: 1 for key in committed if key != missing} for missing in committed]
        committed_query, query = self._query(repo, committed, *results)

        with pytest.raises(RuntimeError):
            committed_query.fetch(query)


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


class TestDump:
    """DUMP"""

    def test_writes_quotes_unquoted(self, tmp_path):
        """should write a value holding a quote as it is, since the runtime splits rows on tabs rather than parsing csv"""
        index.dump_data([CurrencyModel(id=1, name='The "Peso"', alpha3="XPS", numeric=None)], tmp_path / "demo.tsv")

        assert (tmp_path / "demo.tsv").read_text(encoding="utf-8") == 'The "Peso"\tXPS\t\n'

    @pytest.mark.parametrize("name", ["Tab\tName", "Line\nName", "Return\rName"])
    def test_raises_on_row_breaking_value(self, tmp_path, name):
        """should raise on a value holding a tab or line break, which would split its row"""
        with pytest.raises(ValueError):
            index.dump_data([CurrencyModel(id=1, name=name, alpha3="XPS", numeric=None)], tmp_path / "demo.tsv")

    def test_raises_on_separator_in_cell_value(self):
        """should raise on a multi-value cell's value holding "|", which the runtime would split in two"""
        with pytest.raises(ValueError):
            ScriptModel(id=1, name="Demo", alpha4="Dmoo", numeric=None, aliases=["a|b"]).to_row()

    def test_row_fields_skip_unshipped(self):
        """should leave a model's UNSHIPPED_FIELDS out of its row, keeping the rest in field order"""
        assert SubdivisionModel.row_fields()[0] == "name"
        assert not {"id", "hashid", "parent_iso_code"} & set(SubdivisionModel.row_fields())

    def test_lookup_splits_keys(self, tmp_path):
        """should write all-digit keys to the integer index and the rest to the string index, each sorted"""
        index.dump_lookup_index([CurrencyModel(id=1, name="B", alpha3="BBB", numeric=8), CurrencyModel(id=2, name="A", alpha3="AAA", numeric=4)], tmp_path)

        assert (tmp_path / "lookup_index_str.tsv").read_text(encoding="utf-8") == "aaa\t2\nbbb\t1\n"
        assert (tmp_path / "lookup_index_int.tsv").read_text(encoding="utf-8") == "4\t2\n8\t1\n"

    def test_lookup_raises_on_shared_key(self, tmp_path):
        """should raise on a lookup key two records hold, writing no index"""
        currencies = [CurrencyModel(id=1, name="A", alpha3="AAA", numeric=None), CurrencyModel(id=2, name="B", alpha3="AAA", numeric=None)]

        with pytest.raises(ValueError):
            index.dump_lookup_index(currencies, tmp_path)
        assert not (tmp_path / "lookup_index_str.tsv").exists()

    def test_postings_little_endian(self, tmp_path):
        """should pack each key's sorted ids as little-endian uint32, with its offset and count"""
        index._dump_inverted_index({("b",): [9], ("a",): [2, 1]}, tmp_path / "demo")

        assert gzip.decompress((tmp_path / "demo.bin.gz").read_bytes()) == struct.pack("<3I", 1, 2, 9)
        assert (tmp_path / "demo_offsets.tsv").read_text(encoding="utf-8") == "a\t0\t2\nb\t2\t1\n"

    def test_registry_numbers_ids_by_row(self, monkeypatch, tmp_path):
        """should number a registry's records by row before writing them, whatever ids they held"""
        monkeypatch.setattr(index, "STAGED_DATA_PATH", tmp_path)
        currencies = [CurrencyModel(id=7, name="B", alpha3="BBB", numeric=None), CurrencyModel(name="A", alpha3="AAA", numeric=None)]

        index.dump_registry("demo", currencies, queryable=False)

        assert [c.id for c in currencies] == [1, 2]
        assert (tmp_path / "demo" / "lookup_index_str.tsv").read_text(encoding="utf-8") == "aaa\t2\nbbb\t1\n"
