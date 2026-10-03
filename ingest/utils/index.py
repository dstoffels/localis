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


def dump_search_index(data: Sequence[Model], datadir_path: Path) -> None:
    blob_path = datadir_path / "search_index.bin.gz"
    offsets_path = datadir_path / "search_index_offsets.tsv"
    search_fields_path = datadir_path / "search_fields.tsv"

    index: dict[str, set[int]] = defaultdict(set)

    # Build posting lists for each trigram
    for item in data:
        for trigram in item.extract_search_trigrams():
            index[trigram].add(item.id)

    buf = bytearray()
    offset = 0
    offsets_rows: list[tuple[str, int, int]] = []

    # Encode each trigram's posting list and record its offset and length
    # sorted for deterministic output
    for trigram in sorted(index):
        ids = sorted(index[trigram])
        buf += array("I", ids).tobytes()
        offsets_rows.append((trigram, offset, len(ids)))
        offset += len(ids)

    # Write the compressed blob to disk
    # mtime=0: gzip otherwise embeds the current time, so identical data would produce different bytes on every dump. The OS header byte (index 9) also varies by Python version (3.11 writes the host OS, later versions 255), so it's pinned to 255 ("unknown")
    blob = bytearray(gzip.compress(buf, compresslevel=6, mtime=0))
    blob[9] = 255
    blob_path.write_bytes(blob)

    # Write the offsets to TSV
    with open(offsets_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerows(offsets_rows)

    with open(search_fields_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for field_name, weight in data[0].SEARCH_FIELDS.items():
            writer.writerow([field_name, weight])
