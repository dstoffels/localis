from http.client import HTTPException, HTTPResponse
import hashlib
import json
import time
import zipfile
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen, Request
from typing import Any, cast
from .logger import ingest_log
from .staging import staged_path, fetched_path

# sent with every request to a data source
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"
SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
# tries per SPARQL query, waiting SPARQL_BACKOFF seconds before the first retry and doubling each time
SPARQL_ATTEMPTS = 4
SPARQL_BACKOFF = 10

# each source file's entry, {url, etag, sha256}, keyed by its file name
_Manifest = dict[str, Any]


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


def _etag(url: str) -> str | None:
    head_request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    head_response = cast(HTTPResponse, urlopen(head_request, timeout=60))
    with head_response:
        return head_response.headers.get("ETag")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _download(url: str, dest: Path) -> str | None:
    """Downloads url to dest via a .part file, returning the ETag of the bytes downloaded."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    request = Request(url, headers={"User-Agent": USER_AGENT})
    ingest_log.writeline(f"Downloading {dest.name} from {url}")
    response = cast(HTTPResponse, urlopen(request, timeout=60))
    with response, open(tmp, "wb") as f:
        etag = response.headers.get("ETag")
        while chunk := response.read(1024 * 1024):
            f.write(chunk)
    tmp.replace(dest)
    return etag


def fetch(url: str, dest: Path, manifest_path: Path, extract: str | None = None) -> bool:
    """Downloads url to dest, extracting a zip's `extract` member, unless the local file matches its last record; stages its manifest entry either way. True if it downloaded."""
    local = dest.with_name(extract) if extract else dest
    etag = _etag(url)
    # a failed run since the last promotion may have downloaded past the committed manifest
    entry = _load_manifest(fetched_path(manifest_path)).get(dest.name) or _load_manifest(manifest_path).get(dest.name, {})
    # hashed only when the ETag matches, so a changed source isn't hashed just to be replaced
    sha256 = _sha256(local) if local.exists() and etag == entry.get("etag") else None
    current = sha256 is not None and sha256 == entry.get("sha256")

    if not current:
        etag = _download(url, dest)
        if extract:
            with zipfile.ZipFile(dest) as zf:
                zf.extract(extract, dest.parent)
            dest.unlink()
        sha256 = _sha256(local)
        ingest_log.writeline(f"Downloaded and updated {local.name}")
    else:
        ingest_log.writeline(f"No update needed for {local.name}")
    # staged manifests hold this run's entries alone, so unused sources drop out
    staged = staged_path(manifest_path)
    entries = _load_manifest(staged)
    entries[dest.name] = {"url": url, "etag": etag, "sha256": sha256}
    _save_manifest(staged, dict(sorted(entries.items())))
    return not current


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
