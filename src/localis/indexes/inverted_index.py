import csv
import gzip
from array import array
from pathlib import Path
from typing import Iterator

# an offsets row: the key's columns (a trigram, or a filter field and value), then the offset and count of its posting list in the packed postings
OffsetsRow = tuple[list[str], int, int]


def _offsets_rows(path: Path) -> Iterator[OffsetsRow]:
    with open(path, "r", newline="", encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t"):
            yield row[:-2], int(row[-2]), int(row[-1])


def read_inverted_index(prefix: Path) -> tuple[array, Iterator[OffsetsRow]]:
    """An inverted index written at ingest: its packed postings (<prefix>.bin.gz) and its offsets rows (<prefix>_offsets.tsv), in key order; empty for a missing index."""
    blob_path = prefix.with_name(prefix.name + ".bin.gz")
    if not blob_path.exists():
        return array("I"), iter(())
    with gzip.open(blob_path, "rb") as f:
        postings = array("I")
        postings.frombytes(f.read())
    return postings, _offsets_rows(prefix.with_name(prefix.name + "_offsets.tsv"))


def keep_allowed(ids: array, allowed_ids: set[int] | None) -> array:
    """The ids in allowed_ids, or all of them when there's no filter."""
    return ids if allowed_ids is None else array("I", (id for id in ids if id in allowed_ids))
