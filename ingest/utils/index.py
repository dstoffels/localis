import csv
from pathlib import Path
from collections import defaultdict
from typing import Sequence
from ingest.shared.models import Model
from array import array
import gzip


def dump_data(data: Sequence[Model], file_path: Path) -> None:
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for item in data:
            writer.writerow(item.to_row())


def dump_lookup_index(data: Sequence[Model], datadir_path: Path) -> None:
    str_path = datadir_path / "lookup_index_str.tsv"
    int_path = datadir_path / "lookup_index_int.tsv"

    str_pairs: list[tuple[str, int]] = []
    int_pairs: list[tuple[int, int]] = []

    for item in data:
        for value in item.extract_lookup_values():
            key = str(value)
            if item.NUMERIC_LOOKUP and key.isdigit():
                int_pairs.append((int(key), item.id))
            else:
                str_pairs.append((key, item.id))

    for path, pairs in ((str_path, str_pairs), (int_path, int_pairs)):
        # an index with no keys isn't written; removing it also clears one left by an earlier dump that had keys
        if not pairs:
            path.unlink(missing_ok=True)
            continue
        pairs.sort()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter="\t", lineterminator="\n")
            writer.writerows(pairs)


def dump_filter_index(data: Sequence[Model], datadir_path: Path) -> None:
    path = datadir_path / "filter_index.tsv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        headers = data[0].FILTER_FIELDS.keys()
        writer.writerow(headers)
        for item in data:
            row = []
            for _, values in item.extract_filter_values().items():
                # skip only missing values: a plain truthiness check would drop a real 0, such as admin_level=0
                row.append("|".join([str(v) for v in values if v is not None and v != ""]))
            writer.writerow(row)


def _gzip(buf: bytes | bytearray) -> bytes:
    # mtime=0: gzip otherwise embeds the current time, so identical data would produce different bytes on every dump. The OS header byte (index 9) also varies by Python version (3.11 writes the host OS, later versions 255), so it's pinned to 255 ("unknown")
    blob = bytearray(gzip.compress(buf, compresslevel=6, mtime=0))
    blob[9] = 255
    return bytes(blob)


def _dump_trigram_index(trigram_sets: dict[int, set[str]], prefix: Path) -> None:
    """Writes one trigram index: its posting lists (<prefix>.bin.gz) and each trigram's offset into them (<prefix>_offsets.tsv); an index with no trigrams isn't written."""
    blob_path, offsets_path = (prefix.with_name(prefix.name + suffix) for suffix in (".bin.gz", "_offsets.tsv"))
    # per-record trigram counts (<prefix>_counts.bin.gz) were dropped when scoring moved to query coverage
    prefix.with_name(prefix.name + "_counts.bin.gz").unlink(missing_ok=True)
    if not any(trigram_sets.values()):
        blob_path.unlink(missing_ok=True)
        offsets_path.unlink(missing_ok=True)
        return

    index: dict[str, list[int]] = defaultdict(list)
    for id in sorted(trigram_sets):
        for trigram in trigram_sets[id]:
            index[trigram].append(id)

    # each trigram's posting list, packed as uint32 and concatenated in trigram order for deterministic output
    buf = bytearray()
    offset = 0
    offsets_rows: list[tuple[str, int, int]] = []
    for trigram in sorted(index):
        ids = index[trigram]
        buf += array("I", ids).tobytes()
        offsets_rows.append((trigram, offset, len(ids)))
        offset += len(ids)
    blob_path.write_bytes(_gzip(buf))

    with open(offsets_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerows(offsets_rows)


def _dump_short_names(data: Sequence[Model], path: Path) -> None:
    """Writes each record's short one-word names as name/id lines, sorted by length then name; not written for a model without SHORT_NAMES, or with no such names."""
    rows = sorted({(name, item.id) for item in data if item.SHORT_NAMES for name in item.extract_short_names()}, key=lambda r: (len(r[0]), r[0], r[1]))
    if not rows:
        path.unlink(missing_ok=True)
        return
    path.write_bytes(_gzip("".join(f"{name}\t{id}\n" for name, id in rows).encode("utf-8")))


def dump_search_index(data: Sequence[Model], datadir_path: Path) -> None:
    """Writes the canon index, from the fields naming each record, the context index, from the fields locating it, and the short-name list for edit-distance matching."""
    _dump_trigram_index({item.id: item.extract_canon_trigrams() for item in data}, datadir_path / "canon_index")
    _dump_trigram_index({item.id: item.extract_context_trigrams() for item in data}, datadir_path / "context_index")
    _dump_short_names(data, datadir_path / "short_names.tsv.gz")
