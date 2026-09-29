from http.client import HTTPResponse
import json
from pathlib import Path
from urllib.request import urlopen, Request
from typing import cast
from data.utils.logger import log

# Fetch URLs
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"

_ManifestEntry = dict[str, str | None]
_Manifest = dict[str, _ManifestEntry]


def _load_manifest(path: Path) -> _Manifest:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(path: Path, manifest: _Manifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def _head_signals(url: str) -> _ManifestEntry:
    head_request = Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    head_response = cast(HTTPResponse, urlopen(head_request, timeout=60))
    with head_response:
        return {
            "etag": head_response.headers.get("ETag"),
            "last_modified": head_response.headers.get("Last-Modified"),
            "content_length": head_response.headers.get("Content-Length"),
        }


def has_changed(url: str, dest: Path, manifest_path: Path) -> bool:
    """Read-only HEAD check against manifest_path; never downloads or writes."""
    manifest = _load_manifest(manifest_path)
    signals = _head_signals(url)

    if signals == manifest.get(dest.name):
        log.writeline(f"No update needed for {dest.name}")
        return False

    return True


def download(url: str, dest: Path, manifest_path: Path) -> None:
    """Unconditional fetch via a .part temp file; pair with has_changed()."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")

    request = Request(url, headers={"User-Agent": USER_AGENT})
    log.writeline(f"Downloading {dest.name} from {url}")
    response = cast(HTTPResponse, urlopen(request, timeout=60))
    with response, open(tmp, "wb") as f:
        while chunk := response.read(1024 * 1024):
            f.write(chunk)

    tmp.replace(dest)
    log.writeline(f"Downloaded and updated {dest.name}")

    manifest = _load_manifest(manifest_path)
    manifest[dest.name] = _head_signals(url)
    _save_manifest(manifest_path, manifest)
