import csv
import sys
from pathlib import Path
from collections import defaultdict
from typing import Iterable, Sequence
from ingest.shared.models import Model
from array import array
import gzip
from localis.indexes.filter_index import MISSING_KEY
from .paths import STAGED_DATA_PATH
from .logger import ingest_log

# each key's columns (a trigram, or a filter field and value) to the ids of the records holding it
InvertedIndex = dict[tuple[str, ...], list[int]]


def _write_tsv(rows: Iterable[Iterable[object]], path: Path) -> None:
    """Writes rows for the runtime's line.split("\\t"), unquoted, None as an empty cell; a cell holding a tab or line break raises, since it would split its row."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        for number, row in enumerate(rows, start=1):
            cells = ["" if value is None else str(value) for value in row]
            for cell in cells:
                if "\t" in cell or "\n" in cell or "\r" in cell:
                    raise ValueError(f"{path.name} row {number} has the cell {cell!r}, holding a tab or line break, which would split its row; strip it from the value in the stage that loads it")
            f.write("\t".join(cells) + "\n")


def dump_data(data: Sequence[Model], file_path: Path) -> None:
    _write_tsv((item.to_row() for item in data), file_path)


def dump_lookup_index(data: Sequence[Model], datadir_path: Path) -> None:
    """Writes the lookup index, string and integer keys to their own files, raising on a key more than one record holds, which lookup() couldn't resolve."""
    holders: dict[str | int, dict[int, Model]] = defaultdict(dict)
    for item in data:
        for key in item.extract_lookup_values():
            holders[int(key) if item.NUMERIC_LOOKUP and key.isdigit() else key][item.id] = item

    shared = {key: items for key, items in holders.items() if len(items) > 1}
    for key, items in shared.items():
        ingest_log.writeline(f"lookup key {key!r} is held by {len(items)} records: " + ", ".join(f"{id} {item.name!r}" for id, item in items.items()), level="ERROR")
    if shared:
        raise ValueError(f"{len(shared)} {datadir_path.name} lookup keys are each held by more than one record (logged above), so lookup() can't resolve them; give each record its own key in the stage, or take the field that isn't unique out of LOOKUP_FIELDS")

    str_pairs = sorted((key, id) for key, items in holders.items() if isinstance(key, str) for id in items)
    int_pairs = sorted((key, id) for key, items in holders.items() if isinstance(key, int) for id in items)
    # an index with no keys isn't written
    for path, pairs in ((datadir_path / "lookup_index_str.tsv", str_pairs), (datadir_path / "lookup_index_int.tsv", int_pairs)):
        if pairs:
            _write_tsv(pairs, path)


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
    """Writes an inverted index: its posting lists, packed as little-endian uint32 and concatenated in key order (<prefix>.bin.gz), and each key's columns with its posting list's offset and count (<prefix>_offsets.tsv); an empty index isn't written."""
    if not index:
        return

    postings = array("I")
    offsets_rows: list[tuple[str | int, ...]] = []
    for key in sorted(index):
        ids = sorted(index[key])
        offsets_rows.append((*key, len(postings), len(ids)))
        postings.extend(ids)
    # little-endian whatever the machine, so the shipped bytes read the same everywhere
    if sys.byteorder == "big":
        postings.byteswap()
    prefix.with_name(prefix.name + ".bin.gz").write_bytes(_gzip(postings.tobytes()))

    # read back with csv.reader, so a key holding a quote is quoted
    with open(prefix.with_name(prefix.name + "_offsets.tsv"), "w", newline="", encoding="utf-8") as f:
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
        return
    path.write_bytes(_gzip("".join(f"{name}\t{id}\n" for name, id in rows).encode("utf-8")))


def dump_search_index(data: Sequence[Model], datadir_path: Path) -> None:
    """Writes the canon index, from the fields naming each record, the context index, from the fields locating it, and the short-name list for edit-distance matching."""
    _dump_inverted_index(_invert_trigrams({item.id: item.extract_canon_trigrams() for item in data}), datadir_path / "canon_index")
    _dump_inverted_index(_invert_trigrams({item.id: item.extract_context_trigrams() for item in data}), datadir_path / "context_index")
    _dump_short_names(data, datadir_path / "short_names.tsv.gz")


def dump_registry(name: str, data: Sequence[Model], queryable: bool = True) -> None:
    """Stages a registry's data file and lookup index, plus its filter and search indexes when it's queryable."""
    path = STAGED_DATA_PATH / name
    path.mkdir(parents=True, exist_ok=True)
    # the runtime takes a record's id from its row, so ids are numbered here, before any row reads one; registries dumped earlier numbered the records this one references
    for id, item in enumerate(data, start=1):
        item.id = id
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
