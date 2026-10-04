from http.client import HTTPException, HTTPResponse
import json
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from typing import cast
from .logger import ingest_log

# sent with every request to a data source
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# tries per SPARQL query, waiting SPARQL_BACKOFF seconds before the first retry and doubling each time
SPARQL_ATTEMPTS = 4
SPARQL_BACKOFF = 10

_Manifest = dict[str, str | None]


def _load_manifest(path: Path) -> _Manifest:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(path: Path, manifest: _Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        # a trailing newline, as editors add on save, so a hand-opened manifest doesn't show as changed
        f.write("\n")


# entries fetched this run, written to their manifest only once the stage that consumes them dumps successfully
_pending: dict[Path, _Manifest] = {}


def record_pending(manifest_path: Path, name: str, value: str | None) -> None:
    """Stages a manifest entry to be written by commit_manifest()."""
    _pending.setdefault(manifest_path, {})[name] = value


def committed_value(manifest_path: Path, name: str) -> str | None:
    """The manifest entry as of the last successful dump."""
    return _load_manifest(manifest_path).get(name)


def commit_manifest(manifest_path: Path) -> None:
    """Writes this run's pending entries to the manifest; call only after the consuming stage has dumped, so a failed run leaves its sources marked unconsumed."""
    pending = _pending.pop(manifest_path, None)
    if not pending:
        return
    manifest = _load_manifest(manifest_path)
    manifest.update(pending)
    _save_manifest(manifest_path, manifest)


def _etag(url: str) -> str | None:
    head_request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    head_response = cast(HTTPResponse, urlopen(head_request, timeout=60))
    with head_response:
        return head_response.headers.get("ETag")


def has_changed(
    url: str, dest: Path, manifest_path: Path, exists_path: Path | None = None
) -> bool:
    """Read-only HEAD check against manifest_path; never downloads or writes."""
    if not (exists_path or dest).exists():
        return True

    manifest = _load_manifest(manifest_path)
    etag = _etag(url)

    if etag == manifest.get(dest.name):
        ingest_log.writeline(f"No update needed for {dest.name}")
        return False

    return True


def download(url: str, dest: Path, manifest_path: Path) -> None:
    """Unconditional fetch via a .part temp file; pair with has_changed()."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    request = Request(url, headers={"User-Agent": USER_AGENT})
    ingest_log.writeline(f"Downloading {dest.name} from {url}")
    response = cast(HTTPResponse, urlopen(request, timeout=60))
    with response, open(tmp, "wb") as f:
        # the ETag of the bytes actually downloaded, which a second HEAD could miss if the file changed in between
        etag = response.headers.get("ETag")
        while chunk := response.read(1024 * 1024):
            f.write(chunk)

    tmp.replace(dest)
    ingest_log.writeline(f"Downloaded and updated {dest.name}")
    record_pending(manifest_path, dest.name, etag)


def fetch(url: str, dest: Path, manifest_path: Path, extract: str | None = None) -> bool:
    """Downloads url to dest if it changed since the last consumed download, unpacking a zip's `extract` member beside it and removing the zip; True if it downloaded."""
    if not has_changed(url, dest, manifest_path, exists_path=dest.with_name(extract) if extract else None):
        return False
    download(url, dest, manifest_path)
    if extract:
        with zipfile.ZipFile(dest) as zf:
            zf.extract(extract, dest.parent)
        dest.unlink()
    return True


def _sparql_bindings(request: Request) -> list[dict]:
    with urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))["results"]["bindings"]


def sparql(query: str) -> list[dict]:
    """The result rows of a Wikidata SPARQL query, fetched live, retrying a failed or cut-off response with backoff."""
    # POST, since the query service caches GET responses and a repeat query must reach a server
    request = Request(
        SPARQL_ENDPOINT,
        data=urlencode({"query": query, "format": "json"}).encode(),
        headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
    )
    for retry in range(SPARQL_ATTEMPTS - 1):
        delay = SPARQL_BACKOFF * 2**retry
        try:
            return _sparql_bindings(request)
        except HTTPError as e:
            if e.code != 429 and e.code < 500:
                raise
            retry_after = e.headers.get("Retry-After", "")
            delay = int(retry_after) if retry_after.isdigit() else delay
            failure = f"HTTP {e.code}"
        # a dropped connection or timeout (OSError, HTTPException), or a body cut off mid-stream (ValueError from decoding)
        except (OSError, HTTPException, ValueError) as e:
            failure = type(e).__name__
        ingest_log.writeline(f"Wikidata query failed ({failure}), retrying in {delay}s", level="WARN")
        time.sleep(delay)
    return _sparql_bindings(request)
