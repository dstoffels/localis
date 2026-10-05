import csv
from pathlib import Path
from collections import defaultdict
from typing import Sequence
from ingest.shared.models import Model
from array import array
import gzip
from localis.indexes.filter_index import MISSING_KEY
from .paths import STAGED_DATA_PATH
from .logger import ingest_log

# each key's columns (a trigram, or a filter field and value) to the ids of the records holding it
InvertedIndex = dict[tuple[str, ...], list[int]]


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
        for key in item.extract_lookup_values():
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
    """Writes the filter index, each (field, value)'s posting list, inverted here so loading only slices it; a record with no value in a field is indexed under MISSING_KEY."""
    index: InvertedIndex = defaultdict(list)
    for item in data:
        for field, values in item.extract_filter_values().items():
            for value in [v for v in values if v] or [MISSING_KEY]:
                index[(field, value)].append(item.id)
    _dump_inverted_index(index, datadir_path / "filter_index")


def _gzip(buf: bytes | bytearray) -> bytes:
    # mtime=0: gzip otherwise embeds the current time, so identical data would produce different bytes on every dump. The OS header byte (index 9) also varies by Python version (3.11 writes the host OS, later versions 255), so it's pinned to 255 ("unknown")
    blob = bytearray(gzip.compress(buf, compresslevel=6, mtime=0))
    blob[9] = 255
    return bytes(blob)


def _dump_inverted_index(index: InvertedIndex, prefix: Path) -> None:
    """Writes an inverted index: its posting lists, packed as uint32 and concatenated in key order (<prefix>.bin.gz), and each key's columns with its posting list's offset and count (<prefix>_offsets.tsv); an empty index isn't written."""
    blob_path, offsets_path = (prefix.with_name(prefix.name + suffix) for suffix in (".bin.gz", "_offsets.tsv"))
    if not index:
        blob_path.unlink(missing_ok=True)
        offsets_path.unlink(missing_ok=True)
        return

    buf = bytearray()
    offset = 0
    offsets_rows: list[tuple[str | int, ...]] = []
    for key in sorted(index):
        ids = sorted(index[key])
        buf += array("I", ids).tobytes()
        offsets_rows.append((*key, offset, len(ids)))
        offset += len(ids)
    blob_path.write_bytes(_gzip(buf))

    with open(offsets_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerows(offsets_rows)


def _invert_trigrams(trigram_sets: dict[int, set[str]]) -> InvertedIndex:
    index: InvertedIndex = defaultdict(list)
    for id, trigrams in trigram_sets.items():
        for trigram in trigrams:
            index[(trigram,)].append(id)
    return index


def _dump_short_names(data: Sequence[Model], path: Path) -> None:
    """Writes each record's short one-word names as name/id lines, sorted by length then name; not written for a model without SHORT_NAMES, or with no such names."""
    rows = sorted({(name, item.id) for item in data if item.SHORT_NAMES for name in item.extract_short_names()}, key=lambda r: (len(r[0]), r[0], r[1]))
    if not rows:
        path.unlink(missing_ok=True)
        return
    path.write_bytes(_gzip("".join(f"{name}\t{id}\n" for name, id in rows).encode("utf-8")))


def dump_search_index(data: Sequence[Model], datadir_path: Path) -> None:
    """Writes the canon index, from the fields naming each record, the context index, from the fields locating it, and the short-name list for edit-distance matching."""
    _dump_inverted_index(_invert_trigrams({item.id: item.extract_canon_trigrams() for item in data}), datadir_path / "canon_index")
    _dump_inverted_index(_invert_trigrams({item.id: item.extract_context_trigrams() for item in data}), datadir_path / "context_index")
    _dump_short_names(data, datadir_path / "short_names.tsv.gz")


def dump_registry(name: str, data: Sequence[Model], queryable: bool = True) -> None:
    """Writes a registry's data file and lookup index to its staging directory, promoted to src/localis/data/<name>/ with the rest of the build, plus its filter and search indexes when it's queryable."""
    path = STAGED_DATA_PATH / name
    path.mkdir(parents=True, exist_ok=True)
    ingest_log.writeline(f"Dumping {len(data)} {name}...")
    dump_data(data, path / f"{name}.tsv")

    ingest_log.writeline(f"Dumping {name} lookup indexes...")
    dump_lookup_index(data, path)
    if not queryable:
        return

    ingest_log.writeline(f"Dumping {name} filter index...")
    dump_filter_index(data, path)

    ingest_log.writeline(f"Dumping {name} search index...")
    dump_search_index(data, path)
