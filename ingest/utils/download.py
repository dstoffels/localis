from http.client import HTTPResponse
import json
from pathlib import Path
from urllib.request import urlopen, Request
from typing import cast
from .logger import ingest_log

# Fetch URLs
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"

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
        while chunk := response.read(1024 * 1024):
            f.write(chunk)

    tmp.replace(dest)
    ingest_log.writeline(f"Downloaded and updated {dest.name}")

    manifest = _load_manifest(manifest_path)
    manifest[dest.name] = _etag(url)
    _save_manifest(manifest_path, manifest)
