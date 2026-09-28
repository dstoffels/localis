from http.client import HTTPResponse
import json
from pathlib import Path
import csv
from collections import defaultdict
from localis.models import Model, CountryModel, SubdivisionModel
import base64
from urllib.request import urlopen, Request
from typing import cast
from data.paths import *
from data.logger import log

# Fetch URLs
USER_AGENT = "localis-data-refresh (+https://github.com/dstoffels/localis)"


def load_countries() -> dict[str, CountryModel]:
    ALPHA2_INDEX = 1
    log.writeline("Loading countries...")
    with open(DATA_PATH / "countries" / "countries.tsv", "r", encoding="utf-8") as f:
        reader = csv.reader(f, delimiter="\t")
        return {
            row[ALPHA2_INDEX]: CountryModel(id, *row)
            for id, row in enumerate(reader, start=1)
        }


def load_subdivisions(
    countries: dict[str, CountryModel],
) -> dict[str, SubdivisionModel]:
    log.writeline("Loading Subdivisions...")
    GEONAMES_CODE_INDEX = 1
    COUNTRY_INDEX = 7
    countries_by_id: dict[int, CountryModel] = {c.id: c for c in countries.values()}
    with open(
        DATA_PATH / "subdivisions" / "subdivisions.tsv", "r", encoding="utf-8"
    ) as f:

        subdivisions: dict[str, SubdivisionModel] = {}
        reader = csv.reader(f, delimiter="\t")
        for id, row in enumerate(reader, start=1):
            country = countries_by_id.get(int(row[COUNTRY_INDEX]))
            row = row[:COUNTRY_INDEX] + ([country] if country else [])
            subdivisions[row[GEONAMES_CODE_INDEX]] = SubdivisionModel(id, *row)
        return subdivisions


def dump_data(data: list[Model], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for item in data:
            writer.writerow(item.to_row())


def dump_lookup_index(data: list[Model], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for item in data:
            row = []
            for value in item.extract_lookup_values():
                row.append(str(value))
            writer.writerow(["|".join(row)])


def dump_filter_index(data: list[Model], path: Path) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        headers = data[0].FILTER_FIELDS.keys()
        writer.writerow(headers)
        for item in data:
            row = []
            for _, values in item.extract_filter_values().items():
                row.append("|".join([str(v) for v in values if v]))
            writer.writerow(row)


def _delta_encode(ids: list[int]) -> list[int]:
    ids.sort()
    out = []
    prev = 0
    for i in ids:
        out.append(i - prev)
        prev = i
    return out


def _varint_encode(value: int) -> bytes:
    out = bytearray()
    while True:
        b = value & 0x7F
        value >>= 7
        if value:
            out.append(b | 0x80)
        else:
            out.append(b)
            break
    return bytes(out)


def encode_id_list(ids: set[int]) -> str:
    """Convert {1,5,6,...} → base64(varint(delta(ids)))"""
    deltas = _delta_encode(list(ids))

    # concat varints
    buf = bytearray()
    for d in deltas:
        buf.extend(_varint_encode(d))

    # Base64 encode for safe TSV storage
    return base64.b64encode(buf).decode("ascii")


def dump_search_index(data: list[Model], path: Path) -> None:
    index: dict[str, set[int]] = defaultdict(set)

    # Build posting lists
    for item in data:
        for trigram in item.extract_search_trigrams():
            index[trigram].add(item.id)

    # Write compressed format
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")

        for trigram, ids in index.items():
            encoded = encode_id_list(ids)
            writer.writerow([trigram, encoded])


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
