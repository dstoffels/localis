import csv
import base64
from pathlib import Path
from collections import defaultdict
from localis.models import Model, CountryModel, SubdivisionModel
from data.utils.paths import DATA_PATH
from data.utils.logger import log
from array import array
import gzip


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


def dump_data(data: list[Model], file_path: Path) -> None:
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for item in data:
            writer.writerow(item.to_row())


def dump_lookup_index(data: list[Model], datadir_path: Path) -> None:
    path = datadir_path / "lookup_index.tsv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        for item in data:
            row = []
            for value in item.extract_lookup_values():
                row.append(str(value))
            writer.writerow(["|".join(row)])


def dump_filter_index(data: list[Model], datadir_path: Path) -> None:
    path = datadir_path / "filter_index.tsv"
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        headers = data[0].FILTER_FIELDS.keys()
        writer.writerow(headers)
        for item in data:
            row = []
            for _, values in item.extract_filter_values().items():
                row.append("|".join([str(v) for v in values if v]))
            writer.writerow(row)


def dump_search_index(data: list[Model], datadir_path: Path) -> None:
    blob_path = datadir_path / "search_index.bin.gz"
    offsets_path = datadir_path / "search_index_offsets.tsv"
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
    blob_path.write_bytes(gzip.compress(buf, compresslevel=6))

    # Write the offsets to TSV
    with open(offsets_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, delimiter="\t", lineterminator="\n")
        writer.writerows(offsets_rows)
