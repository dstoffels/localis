import hashlib
import io
import zipfile
from email.message import Message
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError
import pytest
from ingest.utils import download, staging
from ingest.utils.committed_query import CONFIRM_QUERIES, CommittedQuery
from utils import read_json, write_json


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


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


class TestFetch:
    """FETCH"""

    def test_downloads_missing_source(self, monkeypatch, inputs, manifest):
        """should download a source missing locally and stage its url, ETag and SHA-256, leaving the committed manifest alone"""
        source = Source(monkeypatch, b"v1", '"1"')

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert (inputs / "source.txt").read_bytes() == b"v1"
        assert read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}
        assert not manifest.exists()

    def test_skips_current_source(self, monkeypatch, inputs, manifest):
        """should not download a source whose local file matches the committed manifest's ETag and SHA-256"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        write_json(manifest, {"source.txt": source.entry()})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert source.downloads == 0
        assert read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_changed_etag(self, monkeypatch, inputs, manifest):
        """should download a source whose ETag differs from its record"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        write_json(manifest, {"source.txt": source.entry()})
        source.content, source.etag = b"v2", '"2"'

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert (inputs / "source.txt").read_bytes() == b"v2"
        assert read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_changed_url(self, monkeypatch, inputs, manifest):
        """should download a source whose url differs from its record, even under the same ETag"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        write_json(manifest, {"source.txt": {**source.entry(), "url": "https://example.org/old"}})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert source.downloads == 1
        assert read_json(staging.staged_path(manifest)) == {"source.txt": source.entry()}

    def test_downloads_altered_local_file(self, monkeypatch, inputs, manifest):
        """should download a source whose local file no longer matches its recorded SHA-256, even under the same ETag"""
        source = Source(monkeypatch, b"v1", '"1"')
        write_json(manifest, {"source.txt": source.entry()})
        (inputs / "source.txt").write_bytes(b"edited")

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert (inputs / "source.txt").read_bytes() == b"v1"

    def test_rerun_after_failed_run(self, monkeypatch, inputs, manifest):
        """should not download again on a rerun what a run that never promoted already downloaded"""
        source = Source(monkeypatch, b"v1", '"1"')
        (inputs / "source.txt").parent.mkdir(parents=True)
        (inputs / "source.txt").write_bytes(b"v1")
        write_json(manifest, {"source.txt": source.entry()})
        source.content, source.etag = b"v2", '"2"'
        download.fetch(Source.URL, inputs / "source.txt", manifest)

        staging.reset_staging()
        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert source.downloads == 1

    def test_drops_unused_entries(self, monkeypatch, inputs, manifest):
        """should stage a manifest holding only the sources this run fetched"""
        source = Source(monkeypatch, b"v1", '"1"')
        write_json(manifest, {"source.txt": source.entry(), "unused.txt": source.entry()})

        download.fetch(Source.URL, inputs / "source.txt", manifest)

        assert read_json(staging.staged_path(manifest)).keys() == {"source.txt"}

    def test_extracts_zip_member(self, monkeypatch, inputs, manifest):
        """should extract the zip's member, remove the zip and record the member under its own name"""
        archive = io.BytesIO()
        with zipfile.ZipFile(archive, "w") as zf:
            zf.writestr("source.txt", b"v1")
        Source(monkeypatch, archive.getvalue(), '"1"')

        download.fetch(Source.URL, inputs / "source.zip", manifest, extract="source.txt")

        assert (inputs / "source.txt").read_bytes() == b"v1"
        assert not (inputs / "source.zip").exists()
        assert read_json(staging.staged_path(manifest)) == {"source.txt": {"url": Source.URL, "etag": '"1"', "sha256": _sha256(b"v1")}}


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
        """should retry a 5xx, a 429, a timeout, a cut-off body or one cut off mid-decode (ValueError)"""
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
        write_json(committed_query.path, committed)
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
