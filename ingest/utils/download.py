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


# entries recorded this run, written to their manifests only when the pipeline promotes its build
_pending: dict[Path, _Manifest] = {}


def commit_manifests() -> None:
    """Writes each manifest as this run's entries alone, since every run fetches every source, so a source no longer used leaves no stale entry; called only on promotion, so a failed run leaves the manifests describing the shipped build."""
    for manifest_path, pending in _pending.items():
        _save_manifest(manifest_path, dict(sorted(pending.items())))
    _pending.clear()


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
    """Downloads url to dest via a .part temp file; the ETag of the bytes downloaded, which a second HEAD could miss if the file changed in between."""
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
    """Downloads url to dest, unpacking a zip's `extract` member beside it and removing the zip, unless the file the stage reads is already the one the manifest records under the same ETag; stages its manifest entry either way. True if it downloaded."""
    local = dest.with_name(extract) if extract else dest
    etag = _etag(url)
    entry = _load_manifest(manifest_path).get(dest.name, {})
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
    _pending.setdefault(manifest_path, {})[dest.name] = {"url": url, "etag": etag, "sha256": sha256}
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
